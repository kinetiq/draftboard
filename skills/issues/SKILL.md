---
name: issues
description: Show Draftboard's structure issues and the author's own notes for the chapter or scene being worked on, add or resolve notes, and check whether a revision addresses a finding. Use when asked "what issues am I in", what to fix in this chapter or scene, whether a change helps a structural finding, or to add a note or issue to a chapter or scene.
---

# Draftboard: unit issues

Read `${CLAUDE_PLUGIN_ROOT}/references/issues.md` and follow it.

Keep answers short: one line per item, no preamble or recap.

Claude Code details:

- A PostToolUse hook already adds a short summary the first time a chapter file is read or edited in a session. Use it, and open the full brief when you need the problem, suggestion or evidence.
- For a single-file script, the hook cannot tell which scene is meant. Ask, or use the scene the conversation is about.
- If no unit is named and none has been opened, ask which one.
