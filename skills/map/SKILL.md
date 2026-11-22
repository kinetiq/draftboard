---
name: map
description: Run Draftboard's full structural analysis of a finished draft (novel or screenplay) - six craft frameworks read the whole work in parallel, then build an interactive map of where they agree and a brief for every chapter or scene. Use when asked to map, diagnose, or analyze the structure of a whole draft, run Draftboard or the frameworks, or rebuild the explorer. Multi-agent and whole-work only.
---

# Draftboard: map the work

Read `${CLAUDE_PLUGIN_ROOT}/references/composer.md` and follow it step by step. In it:

- `<plugin>` is `${CLAUDE_PLUGIN_ROOT}`.
- `<script>` is `python "${CLAUDE_PLUGIN_ROOT}/scripts/draftboard.py"`. If `python` is not found, try `python3`, then `py -3`.

Keep every message to the writer short: no preamble, no recaps, progress updates of one line per stage.

Claude Code details:

1. If the project has no `draftboard.json`, run the setup skill first (`/draftboard:setup`).
2. Confirm the lineup with AskUserQuestion. Ask whether to run the standard six, and offer the two optional frameworks as add-ons with their one-line "add it when" reason from the composer's table (theme: the story argues a moral question; opposition: several antagonists or rivals). Recommend them only when the work fits that reason. Put the core six first, say the agent count, and give a usage estimate scaled to the word count: about 2 million tokens for a 170,000-word novel (roughly 12 tokens per word, with a floor of about 150,000 for very short works). Above 60,000 words, add that it can use a large share of a session's limits on smaller plans. Keep the question to two or three lines.
3. Keep a task list with one item per composer step.
4. Start agents with the Agent tool, `subagent_type: general-purpose`, all agents of a stage in the same message so they run in parallel. Give every agent absolute paths: its brief under `${CLAUDE_PLUGIN_ROOT}/references/frameworks/`, the run folder, `chapters.json`, `ledger.json`, `draftboard.json`, and the text files.
5. Do the finding checks and the agreement step yourself, not in a subagent.
6. Never hand-edit the generated `explorer.html` or briefs. Change the JSON and rebuild.
7. **Rebuild only** ("rebuild the explorer"): run `<script> build <latest run folder>`; no agents. `latest.json` in the runs folder names the latest run per volume.
