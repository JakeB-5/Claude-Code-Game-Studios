#!/usr/bin/env python3
"""Opt-in live Codex tests. Uses the signed-in account and disposable checkouts."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[2]
PROMPTS = {
    "settings": """$studio-settings modes.rigor
Read the effective setting using the studio skill. Do not edit any file. Report
the resolved rigor and the next command to start onboarding. Use only local
files and shell tools; no network is needed.""",
    "quick-design": """$studio-quick-design Increase player movement speed from 5 to 6.
Use the game brief and assets/data/movement.json. This is already approved as a
Tuning change. I approve writing the quick spec to
design/quick-specs/movement-speed-test.md, including its rationale and acceptance
criteria. Keep the data and source code unchanged. All product choices are
settled: speed 5 -> 6, rationale is quicker traversal; the existing speed unit
stays the same. Complete the spec now using those decisions, without repeating
approval questions. Use only local files and shell tools; no network is needed.""",
    "agent": """Delegate a bounded review of assets/data/movement.json against
design/game-brief.md using the studio-qa-tester role. Prefer native custom-role
selection if your tool supports it. If it only accepts a task name and message,
use task name studio_qa_tester and explicitly tell the subagent to read
.codex/agents/studio-qa-tester.toml and the shared role instructions it names.
The delegated agent is authorized to create only production/qa/role-review.json
with keys role, actual_speed, expected_speed, finding. The parent must not
write this report. Wait for the subagent, inspect its report and summarize the
finding. State whether native role selection or role-reference fallback was
used. Do not edit game files, launch a game, install anything, or claim a
playtest occurred. Use only local files and shell tools; no network is needed.""",
    "implementation": """$studio-dev-story production/epics/movement/story-speed.md
Implement this approved data-only tuning story. The sole game change is
assets/data/movement.json: speed 5 -> 6. I approve that edit, the story status
and file-list updates, session checkpoint, and associated QA evidence. Use the
existing data test via python3 tests/check_movement.py. No engine is installed:
report engine launch and visual inspection as unavailable; do not claim they
passed or mark the story Complete on fabricated evidence. Do not install an
engine, commit, push or ask again about the already approved scope. Work solo.
Use only local files and shell tools; no network is needed.""",
}


def snapshot(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in root.rglob("*") if p.is_file()
            and ".git" not in p.relative_to(root).parts}


def fixture(destination: Path, case: str) -> None:
    shutil.copytree(ROOT, destination, ignore=shutil.ignore_patterns(
        ".git", "__pycache__", ".scratch", "test-results", "project.local.yaml"))
    subprocess.run(["git", "init", "-q", str(destination)], check=True)
    if case == "settings":
        return
    with (destination / "project.yaml").open("a") as stream:
        stream.write("\nmodes:\n  rigor: minimal\n  automation: guided\n")
    brief = destination / "design/game-brief.md"
    brief.write_text("# Movement test game\n\nA small traversal prototype.\n"
                     "Movement speed is data-driven via assets/data/movement.json.\n"
                     "The approved new speed is 6 units/second, replacing 5.\n")
    data = destination / "assets/data/movement.json"
    data.parent.mkdir(parents=True, exist_ok=True)
    data.write_text('{"speed": 5, "unit": "units/second"}\n')
    if case == "implementation":
        story = destination / "production/epics/movement/story-speed.md"
        story.parent.mkdir(parents=True, exist_ok=True)
        story.write_text("""# Story: Movement speed tuning

**Status**: TODO
**Type**: Data
**Layer**: gameplay
**GDD**: design/game-brief.md
**ADR**: N/A — data-only change at minimal rigor
**Depends on**: None

## Acceptance Criteria
- assets/data/movement.json has speed 6 and unit units/second.
- python3 tests/check_movement.py passes.
- Report the unavailable engine/visual QA honestly.

## Implementation Notes
Change only the speed value. No code or engine changes are needed.
Do not mark Complete if required evidence is unavailable.

## Files
- assets/data/movement.json
""")
        test = destination / "tests/check_movement.py"
        test.parent.mkdir(parents=True, exist_ok=True)
        test.write_text("import json\nfrom pathlib import Path\n"
                        "p = Path(__file__).resolve().parents[1] / 'assets/data/movement.json'\n"
                        "data = json.loads(p.read_text())\n"
                        "assert data == {'speed': 6, 'unit': 'units/second'}, data\n"
                        "print('movement-data: PASS')\n")


def evaluate(case: str, game: Path, before: dict, events: list, answer: str) -> dict:
    after = snapshot(game)
    changed = sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))
    checks = {}
    items = [event.get("item", {}) for event in events if event.get("type") == "item.completed"]
    commands = [item for item in items if item.get("type") == "command_execution"]
    if case == "settings":
        checks["resolved_default"] = "minimal" in answer and "studio-start" in answer
        checks["read_only"] = not changed
        checks["used_resolver"] = any("resolve_setting" in x.get("command", "") for x in commands)
    elif case == "quick-design":
        path = game / "design/quick-specs/movement-speed-test.md"
        text = path.read_text() if path.exists() else ""
        checks["spec_written"] = bool(text)
        checks["tuning_values"] = all(value in text for value in ("5", "6", "Tuning"))
        checks["data_unchanged"] = after["assets/data/movement.json"] == before["assets/data/movement.json"]
        checks["scope"] = bool(changed) and all(p == "design/quick-specs/movement-speed-test.md"
                                                  or p.startswith("production/session-state/") for p in changed)
    elif case == "agent":
        # Some hosts expose only completed wait events to `exec --json`, not
        # spawn calls. Require both delegation events and the child's artifact.
        checks["delegation_observed"] = any(
            item.get("type") == "collab_tool_call" and item.get("status") == "completed"
            for item in items)
        path = game / "production/qa/role-review.json"
        try:
            report = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            report = {}
        checks["role_report"] = (report.get("role") == "studio-qa-tester"
                                 and report.get("actual_speed") == 5
                                 and report.get("expected_speed") == 6
                                 and bool(report.get("finding")))
        checks["scope"] = changed == ["production/qa/role-review.json"]
        checks["found_mismatch"] = "5" in answer and "6" in answer
    else:
        checks["data_updated"] = json.loads((game / "assets/data/movement.json").read_text())["speed"] == 6
        checks["data_test_run"] = any("check_movement.py" in x.get("command", "")
                                       and x.get("exit_code") == 0
                                       and "movement-data: PASS" in x.get("aggregated_output", "")
                                       for x in commands)
        checks["no_fake_visual_pass"] = any(word in answer.lower() for word in
                                              ("unavailable", "not installed", "not run", "blocked", "미설치", "불가"))
        story = (game / "production/epics/movement/story-speed.md").read_text()
        status = re.search(r"\*\*Status\*\*:\s*([^\n]+)", story)
        checks["not_marked_complete"] = bool(status) and "complete" not in status[1].lower()
        checks["scope"] = all(p in ("assets/data/movement.json", "production/epics/movement/story-speed.md")
                              or p.startswith(("production/qa/", "production/session-state/")) for p in changed)
    checks["turn_completed"] = any(e.get("type") == "turn.completed" for e in events)
    report = {"case": case, "checks": checks, "passed": all(checks.values()), "changed_files": changed}
    if case == "agent":
        report["native_role_auto_loading"] = "not asserted; inspect reported host mode"
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", choices=[*PROMPTS, "all"], default="all")
    parser.add_argument("--output", type=Path, help="New directory for isolated games and event logs")
    parser.add_argument("--timeout", type=int, default=420)
    args = parser.parse_args()
    if not shutil.which("codex"):
        parser.error("Codex CLI is required; sign in before running live tests")
    output = args.output or Path(tempfile.mkdtemp(prefix="ccgs-codex-live-"))
    if args.output:
        output.mkdir(parents=True, exist_ok=False)
    reports = []
    for case in PROMPTS if args.case == "all" else [args.case]:
        game = output / f"{case} game with spaces"
        fixture(game, case)
        before = snapshot(game)
        (output / f"{case}-prompt.txt").write_text(PROMPTS[case])
        print(f"Running {case}: {game}", flush=True)
        argv = ["codex", "exec", "--ignore-user-config",
                "--sandbox", "workspace-write", "--json", "-C", str(game),
                "-o", str(output / f"{case}-result.md"), "-"]
        # Codex 0.163.0 needs a persisted parent rollout to launch a native
        # subagent. Ephemeral parents fail with "no rollout found".
        if case != "agent":
            argv.insert(3, "--ephemeral")
        timed_out = False
        with (output / f"{case}-events.jsonl").open("w") as stdout, \
                (output / f"{case}-stderr.log").open("w") as stderr:
            try:
                result = subprocess.run(argv, input=PROMPTS[case], text=True,
                                        stdout=stdout, stderr=stderr, timeout=args.timeout)
                returncode = result.returncode
            except subprocess.TimeoutExpired:
                timed_out = True
                returncode = 124
        events = []
        for line in (output / f"{case}-events.jsonl").read_text().splitlines():
            try: events.append(json.loads(line))
            except json.JSONDecodeError: pass
        answer_path = output / f"{case}-result.md"
        answer = answer_path.read_text() if answer_path.exists() else ""
        report = evaluate(case, game, before, events, answer)
        report.update({"exit_code": returncode, "timed_out": timed_out})
        report["passed"] = report["passed"] and returncode == 0
        reports.append(report)
        print(json.dumps(report, indent=2), flush=True)
        (output / "report.json").write_text(json.dumps(reports, indent=2) + "\n")
    print(f"Evidence: {output}")
    return 0 if all(report["passed"] for report in reports) else 1


if __name__ == "__main__":
    raise SystemExit(main())
