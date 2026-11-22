---
name: map
description: Run Draftboard's full structural analysis of a finished draft (novel or screenplay) - six craft frameworks read the whole work in parallel, then build an interactive map of where they agree and a brief for every chapter or scene. Use when asked to map, diagnose, or analyze the structure of a whole draft, run Draftboard or the frameworks, or rebuild the explorer. Multi-agent and whole-work only.
---

# Draftboard: map the work

Read `${CLAUDE_PLUGIN_ROOT}/references/composer.md` and follow it step by step. In it:

- `<plugin>` is `${CLAUDE_PLUGIN_ROOT}`.
- `<script>` is `python "${CLAUDE_PLUGIN_ROOT}/scripts/draftboard.py"`. If `python` is not found, try `python3`, then `py -3`.

Claude Code details:

1. If the project has no `draftboard.json`, run the setup skill first (`/draftboard:setup`).
2. Confirm the lineup with AskUserQuestion. Put the core six first and say the agent count.
3. Keep a task list with one item per composer step.
4. Start agents with the Agent tool, `subagent_type: general-purpose`, all agents of a stage in the same message so they run in parallel. Give every agent absolute paths: its brief under `${CLAUDE_PLUGIN_ROOT}/references/frameworks/`, the run folder, `chapters.json`, `ledger.json`, `draftboard.json`, and the text files.
5. Do the finding checks and the agreement step yourself, not in a subagent.
6. Never hand-edit the generated `explorer.html` or briefs. Change the JSON and rebuild.
7. **Rebuild only** ("rebuild the explorer"): run `<script> build <latest run folder>`; no agents. `latest.json` in the runs folder names the latest run per volume.
