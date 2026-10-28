# Codex port verification

Verified on **2026-10-28 (Asia/Seoul)** against upstream v1.2.0,
commit `05ad7c8`, using **Codex CLI 0.163.0**, Python 3.14.7 and macOS.
No model name is pinned by the port or its live test runner.

## Automated checks

| Check | Result |
| --- | --- |
| Generated adapters match current sources | 74 skills and 49 agent configurations pass |
| Skill frontmatter and naming | All 74 pass the Codex skill-creator validator |
| Adapter links | Every runtime and shared-workflow target exists |
| Agent TOML | All 49 parse with the three required fields; no model/permission overrides |
| Shared context preprocessing | All 74 skill entrypoints execute without writing files |
| Behavioral integration suite | 20 tests pass |
| Original `.claude/`, `CLAUDE.md`, `project.yaml`, license | Unmodified from upstream |

The integration suite checks real settings resolution and local overrides,
invalid-setting rejection without mutation, empty commit history,
rejection of unsupported multiline preprocessing, nested working directories and
paths containing spaces, Godot/Unity/Unreal path-rule selection, invalid JSON
asset and staged-commit rejection, generator drift and broken-reference
detection, preservation of user-owned files, and refusal to execute unknown
Markdown preprocessing as shell code. Commit validation does not create a commit.

## Actual Codex sessions

Tests run in disposable copies. The deterministic scripts alone are not counted
as evidence that a model successfully followed a workflow.

| Scenario | Observed behavior |
| --- | --- |
| `$studio-settings modes.rigor` | Discovered the skill, called the shared resolver, reported `minimal` from defaults and `$studio-start` as the next step; no file edits |
| `$studio-quick-design` | Used the approved 5 → 6 speed change, created the specified tuning document with rationale and acceptance criteria, and left game data unchanged |
| `$studio-dev-story` | Changed only the approved game-data value, ran the supplied data test and asset validator, updated the story/evidence/checkpoint, and left the story In Progress because engine/visual evidence was unavailable |
| `studio-qa-tester` role delegation | A real subagent read the role and fixtures, wrote the allowed QA report, and identified actual speed 5 versus expected 6; the parent inspected the report |

The role test used **role-reference fallback**: this host's delegation tool
offers a task name and message, without a native custom-role selector. The
generated native TOML files were validated structurally; native role auto-loading
is **not claimed as verified**. The runtime guide documents both invocation forms.

An initial agent test with `codex exec --ephemeral` failed with `no rollout found`.
The runner now persists the parent session for the agent test so the subagent
can load it. Other cases remain ephemeral. An initial strict native-role test
also correctly reported failure when only the fallback interface was available;
the portable role-delegation test records that mode instead of claiming native
auto-loading passed.

See [verification.json](verification.json) for the machine-readable outcome
summary. Raw event logs stay in the local test directories because they may
include host context; they are not needed to reproduce the tests.

## Scope and remaining limits

- This is **not** a full end-to-end test of all 74 workflows. All 74 adapters
  and context directives were checked; live behavioral coverage is the four
  scenarios above.
- Godot, Unity and Unreal executables were not installed. Engine launch,
  rendered gameplay, editor integration and exports were not tested.
- Claude lifecycle hooks are not automatically installed in Codex. Asset,
  staged-commit and push checks are explicit commands; they are not a sandbox.
- CI covers the deterministic suite on macOS and Linux with Python 3.11.
  Windows and live desktop-app UI operation are not part of this verification.

## Reproduce

```sh
python3 scripts/codex/studio.py check
python3 -m unittest discover -s tests/codex -v
# Requires a signed-in Codex CLI and consumes account usage:
python3 scripts/codex/live_test.py --case all
```

The live runner prints its evidence directory and writes `report.json` there.
It does not install engines, alter the real project's game files, or change
global Codex settings.
