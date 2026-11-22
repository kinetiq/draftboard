---
name: issues
description: Show Draftboard's structure issues and the author's own notes for the chapter or scene being worked on, add or resolve notes, check whether a revision addresses a finding, and mark findings fixed, partly fixed, kept or stale. Use when asked "what issues am I in", what to fix in this chapter or scene, whether a change helps a structural finding, to add a note to a chapter or scene, or when the author says an issue is fixed, done, closed or kept.
---

# Draftboard: unit issues

Read `${CLAUDE_PLUGIN_ROOT}/references/issues.md` and follow it.

Keep answers short: one line per item, no preamble or recap.

Claude Code details:

- A PostToolUse hook already adds a short summary the first time a chapter file is read or edited in a session. Use it, and open the full brief when you need the problem, suggestion or evidence.
- For a single-file script, the hook cannot tell which scene is meant. Ask, or use the scene the conversation is about.
- If no unit is named and none has been opened, ask which one.
- Script: `python "${CLAUDE_PLUGIN_ROOT}/scripts/draftboard.py"`. If `python` is not found, try `python3`, then `py -3`.
- After `status` changes a mark, if `latest.json` has an explorer URL and you have an Artifact tool, publish the run's `explorer.html` to that URL.
