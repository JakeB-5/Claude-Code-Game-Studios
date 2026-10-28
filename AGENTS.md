# Game Studios for Codex

This fork adds Codex to the upstream Claude Code Game Studios template. The game
workflows, role expertise, templates and helper scripts remain in `.claude/` so
upstream updates can be merged. No Claude installation is needed to use Codex.

- Use the `studio-*` skills in `.agents/skills/` for game-studio workflows.
  Start with `$studio-start`; use `$studio-help` to find the next step.
- Before using a studio skill or role, read `docs/codex/runtime.md`. It defines
  the Codex translation of upstream tools, arguments, permissions and hooks.
- Project choices and rigor come from `project.yaml` and `project.local.yaml`;
  use the existing resolver, not guesses or template defaults.
- Before editing game files, run `python3 scripts/codex/studio.py rules PATH...`
  from the repository root and read the matching standards. This also handles
  Unity `Assets/` and Unreal `Source/` paths, not just Godot `src/`.
- Read `production/session-state/active.md` when continuing existing work.
  Record useful progress there; verify stale facts against the current files.
- Use the user's existing decisions and authorization. Do not ask again for
  already-authorized routine edits. Ask about unresolved game direction or
  material scope changes. Never interpret a missing reply as consent.
- Custom `studio-*` agents live in `.codex/agents/`. Delegate when requested
  or when an applicable workflow calls for it and the runtime permits it.
  Otherwise apply the relevant role yourself. Never invent a delegation result.
- Run the game and inspect visible changes before claiming visual QA passed.
  Report unavailable engines, tools or evidence as limitations.

## Maintaining the Codex integration

Edit `scripts/codex/studio.py` to change generated adapters. Then run:

```sh
python3 scripts/codex/studio.py sync
python3 scripts/codex/studio.py check
python3 -m unittest discover -s tests/codex -v
```

Keep upstream `.claude/` and `CLAUDE.md` files intact unless deliberately fixing
upstream behavior. Do not hardcode model names or grant extra permissions in
generated agent files. Keep the MIT license and original attribution.
