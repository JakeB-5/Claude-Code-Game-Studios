"""Behavioral integration tests; every mutation uses a disposable studio copy."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("studio", ROOT / "scripts/codex/studio.py")
studio = importlib.util.module_from_spec(spec)
spec.loader.exec_module(studio)


class StudioTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="studio tests ")
        self.root = Path(self.tmp.name) / "game with spaces"
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns(
            ".git", "__pycache__", ".scratch", "test-results", "project.local.yaml"))
        self.cli = self.root / "scripts/codex/studio.py"

    def tearDown(self):
        self.tmp.cleanup()

    def call(self, *args, cwd=None):
        return subprocess.run([sys.executable, str(self.cli), *args],
                              cwd=cwd or self.root, text=True, capture_output=True)

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, text=True,
                              capture_output=True, check=True)

    def test_generated_links_and_native_agent_schema(self):
        result = self.call("check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("74 skills, 49 agents", result.stdout)

    def test_sync_is_idempotent_and_preserves_shared_sources(self):
        source = self.root / ".claude/skills/start/SKILL.md"
        before = source.read_bytes()
        manifest = (self.root / studio.MANIFEST).read_bytes()
        self.assertEqual(self.call("sync").returncode, 0)
        self.assertEqual(self.call("sync").returncode, 0)
        self.assertEqual((self.root / studio.MANIFEST).read_bytes(), manifest)
        self.assertEqual(source.read_bytes(), before)

    def test_upstream_change_requires_refresh(self):
        source = self.root / ".claude/skills/start/SKILL.md"
        source.write_text(source.read_text() + "\nAdditional upstream guidance.\n")
        self.assertNotEqual(self.call("check").returncode, 0)
        self.assertEqual(self.call("sync").returncode, 0)
        self.assertEqual(self.call("check").returncode, 0)

    def test_broken_reference_is_reported(self):
        path = self.root / ".agents/skills/studio-start/SKILL.md"
        path.write_text(path.read_text().replace("../../../docs/", "../../docs/"))
        result = self.call("check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Broken link", result.stderr)

    def test_sync_preserves_user_owned_files(self):
        path = self.root / ".agents/skills/studio-start/SKILL.md"
        path.write_text("User-created content\n")
        self.assertNotEqual(self.call("sync").returncode, 0)
        self.assertEqual(path.read_text(), "User-created content\n")

    def test_removed_upstream_skill_removes_only_generated_entry(self):
        shutil.rmtree(self.root / ".claude/skills/start")
        self.assertNotEqual(self.call("check").returncode, 0)
        self.assertEqual(self.call("sync").returncode, 0)
        self.assertFalse((self.root / ".agents/skills/studio-start/SKILL.md").exists())

    def test_unknown_preprocessing_fails_without_executing_it(self):
        path = self.root / ".claude/skills/start/SKILL.md"
        path.write_text(path.read_text() + "\n!`touch UNAUTHORIZED`\n")
        result = self.call("context", "start")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unsupported context directive", result.stderr)
        self.assertFalse((self.root / "UNAUTHORIZED").exists())

    def test_argument_injection_is_not_shell_code(self):
        result = self.call("context", "start; touch UNAUTHORIZED")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse((self.root / "UNAUTHORIZED").exists())

    def test_multiline_preprocessing_is_not_silently_skipped(self):
        path = self.root / ".claude/skills/start/SKILL.md"
        path.write_text(path.read_text() + "\n!`echo one\necho two`\n")
        result = self.call("context", "start")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Unsupported multiline", result.stderr)

    def test_changelog_context_accepts_a_repo_without_commits(self):
        self.git("init", "-q")
        result = self.call("context", "changelog")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Commit history unavailable", result.stdout)

    def test_helper_rejects_outside_scripts(self):
        result = self.call("helper", "start", "../../outside.sh")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Helper must", result.stderr)

    def test_context_resolves_real_settings_from_nested_directory(self):
        self.assertEqual(self.call("helper", "settings", "scripts/config-set.sh",
                                   "modes.rigor", "full").returncode, 0)
        result = self.call("context", "help", cwd=self.root / "src")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("workflow: full", result.stdout)
        self.assertFalse((self.root / "src/project.yaml").exists())

    def test_local_override_wins(self):
        (self.root / "project.local.yaml").write_text("modes:\n  review_mode: lean\n")
        result = self.call("helper", "settings", "hooks/yaml-helper.sh",
                           "resolve_setting", "modes.review_mode")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("lean", result.stdout)

    def test_invalid_setting_leaves_project_unchanged(self):
        before = (self.root / "project.yaml").read_bytes()
        result = self.call("helper", "settings", "scripts/config-set.sh",
                           "modes.rigor", "invalid")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((self.root / "project.yaml").read_bytes(), before)

    def test_rule_globs_cover_all_engine_layouts(self):
        paths = ["src/gameplay/player.gd", "Assets/Gameplay/Player.cs",
                 "Assets/Game/gameplay/Player.cs", "Source/Game/Gameplay/Player.cpp"]
        result = self.call("rules", *paths)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("gameplay-code.md", result.stdout)
        for path in paths:
            self.assertIn(path, result.stdout)
        self.assertFalse(studio.glob_matches("Assets/UI/Player.cs", "Assets/**/Gameplay/**/*.cs"))

    def test_shader_and_scene_globs(self):
        result = self.call("rules", "test.tscn", "assets/shaders/water.gdshader")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("scene-files.md", result.stdout)
        self.assertIn("shader-code.md", result.stdout)

    def test_asset_validation_detects_invalid_json_and_accepts_valid(self):
        path = self.root / "assets/data/combat.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"damage":')
        self.assertNotEqual(self.call("validate", "assets", str(path)).returncode, 0)
        path.write_text('{"damage": 10}')
        result = self.call("validate", "assets", str(path), cwd=self.root / "src")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_missing_or_outside_asset_fails_explicitly(self):
        self.assertNotEqual(self.call("validate", "assets", "assets/missing.json").returncode, 0)
        self.assertNotEqual(self.call("validate", "assets", "../outside.json").returncode, 0)
        self.assertNotEqual(self.call("validate", "assets", "README.md").returncode, 0)

    def test_commit_check_detects_staged_invalid_data_without_committing(self):
        self.git("init", "-q")
        path = self.root / "assets/data/combat.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"damage":')
        self.git("add", "assets/data/combat.json")
        result = self.call("validate", "commit")
        self.assertNotEqual(result.returncode, 0, result.stdout)
        self.assertEqual(self.git("diff", "--cached", "--name-only").stdout.strip(),
                         "assets/data/combat.json")
        refs = self.git("for-each-ref").stdout
        self.assertEqual(refs, "")

    def test_all_context_directives_execute_without_writes(self):
        self.git("init", "-q")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "commit", "--allow-empty", "-qm", "Fixture")
        before = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*")
                  if p.is_file() and ".git" not in p.relative_to(self.root).parts}
        for skill in sorted((self.root / ".claude/skills").glob("*/SKILL.md")):
            with self.subTest(skill=skill.parent.name):
                result = self.call("context", skill.parent.name)
                self.assertEqual(result.returncode, 0, result.stderr)
        after = {p.relative_to(self.root): p.read_bytes() for p in self.root.rglob("*")
                 if p.is_file() and ".git" not in p.relative_to(self.root).parts}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
