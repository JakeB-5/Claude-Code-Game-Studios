# Codex runtime translation

Read this once per session when using a studio workflow. This guide adapts the
shared Claude-oriented instructions; it does not change the game's design rules.

## Skill and reference paths

`$studio-NAME` loads `.agents/skills/studio-NAME/SKILL.md`, then the shared
`.claude/skills/NAME/SKILL.md`. Read the latter's body as the workflow. Its YAML
fields such as `model`, `allowed-tools`, `context`, and `agent` are Claude
metadata, not Codex permissions or model settings.

The adapter's Markdown links are relative to the adapter file. Inside the
shared workflow, `references/...` means `.claude/skills/NAME/references/...`.
Other `.claude/...`, `docs/...`, `design/...`, `production/...`, and `src/...`
paths are relative to the repository root. Do not relocate the shared sources.
These repo-local skills require the whole studio checkout; copying only a
SKILL.md into a global skills directory does not install the framework.

`$ARGUMENTS` is the user's text after `$studio-NAME`, used as data, not shell
code. References to `/NAME` mean `$studio-NAME` for a known studio skill.
Translate workflow commands in user-facing answers; do not rename filesystem
paths, Git options, engine commands or `/clear` into imaginary studio commands.

## Commands and preprocessed context

Run helpers with the repository root as the working directory. Find it from
the adapter location or `git rev-parse --show-toplevel`; a session in `src/`
must still operate on the same root project. Quote paths containing spaces.

Before following a shared skill, run:

```sh
python3 scripts/codex/studio.py context NAME
```

This explicitly runs the shared skill's read-only `!` context directives. Codex
does not run Claude's Markdown preprocessing. The tool uses a fixed command
allowlist and argument arrays, never evaluates Markdown as arbitrary shell
code, and fails visibly on an unsupported new directive. Use its actual output
in place of the source's injected block. Do not fall back to default settings
merely because Codex did not preprocess the source. On failure report the
missing context and inspect the project configuration before proceeding.

For subsequent snippets using `${CLAUDE_SKILL_DIR}`, substitute the absolute
path of the **shared** skill directory, `.claude/skills/NAME`, not the adapter.
Alternatively the following bridge sets that variable for one helper process:

```sh
python3 scripts/codex/studio.py helper settings hooks/yaml-helper.sh resolve_setting modes.rigor
python3 scripts/codex/studio.py helper start scripts/project-state.sh
```

The helper command can run mutating upstream helpers too; invoking it requires
the same task authorization as running that helper directly. It never supplies
approval. It preserves stdout, stderr, exit code and the root working directory.

## Tools and collaboration

| Shared term | Codex behavior |
| --- | --- |
| Read / Glob / Grep | Available file tools or bounded shell reads and `rg` |
| Write / Edit | Available file editing tools |
| Bash | Available shell tool, with the repository root as working directory |
| AskUserQuestion | Available question tool, or ask in chat and wait when an answer is required |
| Task / Agent / TeamCreate / SendMessage | Available subagent tools within task authorization; otherwise apply roles sequentially |
| WebSearch / WebFetch | Available search/browser tools; report when unavailable |
| TodoWrite | Available plan tool or a concise task checklist |

Never call a Claude-only tool by its old name. Never claim selectable buttons
exist when asking in plain text. Do not force a model change from an upstream
Opus/Sonnet/Haiku label. Native agents inherit the session model and permissions.
Role `memory`, `skills` and `maxTurns` frontmatter are not automatic Codex
features; read needed skills on demand and use the project checkpoint.

Subagent tool interfaces vary by host. If a custom-role selector is available,
select `studio-NAME`. If the tool only offers a task name and message, give it
a valid task identifier such as `studio_qa_tester` and explicitly instruct it to
read `.codex/agents/studio-qa-tester.toml` and the shared role body. This is a
role-reference fallback, not proof that native role auto-loading occurred.
If no delegation tool is available, apply the role in the parent session and
say so. Never use a task name as though it automatically selected a role.

The user and host instructions govern approval. Shared "May I write?" prompts
do not require repeating approval already given for the same work. Respect
`modes.automation` for choices not already settled by the user; do not silently
change that setting. Skill invocation alone does not approve unrelated writes,
publishing or destructive actions. If a skill needs a choice and none was
provided, ask and stop that dependent work. Read-only workflows remain read-only.

## Rules, hooks and honest evidence

Claude's `settings.json` permissions, hooks and `@` imports are not installed
into Codex by this port. No automatic lifecycle enforcement is claimed.
Directory `AGENTS.md` files link the applicable shared instructions. Before
editing files, run `studio.py rules PATH...` and read its matching rule files.
This is explicit agent guidance, not a sandbox or a security boundary.

Use these explicit checks as appropriate:

```sh
python3 scripts/codex/studio.py validate commit
python3 scripts/codex/studio.py validate assets assets/data/combat.json
python3 scripts/codex/studio.py validate push
```

`commit` validates staged changes. `assets` validates the named existing files.
`push` emits the upstream protected-branch advisory. These commands feed synthetic
tool events to the existing validators; they **never commit or push**. A zero
exit status may include warnings, so read the output. Check required game tests
and real launch/visual evidence separately. Session logging, memory and agent
audit hooks are not run automatically; keep the checkpoint explicitly as needed.

For setup, use `project.yaml` as the source of truth and the pinned engine
reference that matches `engine.name`. Upstream `/setup-engine` may also update
`CLAUDE.md` for Claude compatibility; that file's `@` imports do not configure
Codex. Do not infer the selected engine from the template's default import.
