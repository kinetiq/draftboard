---
name: setup
description: Set up Draftboard for a novel or screenplay project by walking the writer through creating draftboard.json. Use the first time Draftboard is used in a project, when draftboard.json is missing or wrong, or when asked to set up, configure, or change Draftboard's settings (title, protagonist, source files, genre).
---

# Draftboard setup

Create `draftboard.json` at the project root. Detect everything you can, ask only what you can't, and keep every message short.

- Config reference: `${CLAUDE_PLUGIN_ROOT}/references/config.md` (read it first).
- Script: `python "${CLAUDE_PLUGIN_ROOT}/scripts/draftboard.py"`. If `python` is not found, try `python3`, then `py -3`.

## Style

- Every message is a few lines. No preamble, no recaps of earlier messages, no closing summary beyond the hand-off below.
- Never state a count (units, scenes, words) before the script's `check` has reported it. Use its numbers.
- Do not ask about anything you can decide sensibly. Skip optional fields you have no good value for; do not ask the writer to fill them.

## 1. Detect (silently)

- If `draftboard.json` exists: run `check`, show its first line and unit count, and ask whether to change anything. Stop if not.
- Find the source: a folder of numbered text files (chapters, or one file per scene), a `*.fountain` file, or a `*.fdx` file. Note the file-name pattern.
- Title: from a title page (`Title:`), a README, or the folder name.
- Author: from the title page, unless it is clearly a placeholder.
- Protagonist: skim the opening of the first unit or two.
- Form, core genre, and any genre contracts (progression, mystery, romance): your best guess from what you skimmed.
- Context files: character lists, story bibles, notes on accepted choices. Only if they clearly exist.
- Cursor: a `.cursor/` folder.

## 2. Confirm in one message

Your message is exactly this, and nothing else: every value you will write, one per line, then one line asking for confirmation. Do not describe the values instead of listing them, and do not add sentences before or after.

```
Title: Night Ferry
Form: screenplay
Source: night-ferry.fountain
Protagonist: Dee
Genre: Thriller

Reply OK, or correct any line.
```

Add `Author:`, `Lane:`, `Contracts:`, `Comps:`, `Context:` or one `Volume:` line per volume only when you have real values. Use AskUserQuestion only when two answers are equally likely (for example, which of two folders is the manuscript).

## 3. Write and check

1. Write `draftboard.json` per `config.md`. Leave out empty optional fields. Default output folders.
2. Run `check`. If units are missing or wrong, fix `source` and rerun; show the writer the result only if you had to fix something.
3. If there is a `.cursor/` folder, copy `${CLAUDE_PLUGIN_ROOT}/templates/cursor-issues.mdc` to `.cursor/rules/draftboard-issues.mdc`, replacing `{{GLOBS}}` with the source folders as globs (for example `book 1/*.md`) and `{{BRIEFS}}` with the briefs folder. Mention it in the hand-off; do not ask first.

## 4. Hand-off

Exactly this, filled from the check, with the blank lines as shown:

```
Draftboard is set up for <Title>. <N> <chapters|scenes>, <words> words. Estimated token usage: <estimate>+ tokens.

You can change these settings anytime with /draftboard:setup.

Start the next step with /draftboard:map

Note: Use a capable model! The latest Opus on Medium works well.
```

Estimate usage as: 25,000 per agent + 7 per word + 150,000 for the main session. Agents = one reader per 43,000 words (at least one) + the tension agent + one per framework (6 by default). For example, an 8-scene short script is about 350,000 tokens, and a 170,000-word novel is about 1,600,000. Round to two significant figures and write it with commas. Above 60,000 words, add to the first paragraph: "This is a large run; it can use a big share of a session's limits on smaller plans." If you added a Cursor rule, add a line before the note: "Added a Cursor rule so Cursor sees each <chapter|scene>'s brief."

Never edit the manuscript or script.
