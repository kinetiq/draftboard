---
name: setup
description: Set up Draftboard for a novel or screenplay project by walking the writer through creating draftboard.json. Use the first time Draftboard is used in a project, when draftboard.json is missing or wrong, or when asked to set up, configure, or change Draftboard's settings (title, protagonist, source files, genre).
---

# Draftboard setup

Walk the writer through creating `draftboard.json` at the root of their project. Ask, do not interrogate: detect what you can, propose it, and let them confirm. The whole thing should take a couple of minutes.

- Plugin folder: `${CLAUDE_PLUGIN_ROOT}`
- Config reference (read it first): `${CLAUDE_PLUGIN_ROOT}/references/config.md`
- Script: `python "${CLAUDE_PLUGIN_ROOT}/scripts/draftboard.py"`. If `python` is not found, try `python3`, then `py -3`. It needs Python 3.10 or newer and nothing else.

## 1. Look before asking

1. If `draftboard.json` already exists, run the script with `check` and show the result. Ask whether to keep it, change a few settings, or start over. Only continue if they want changes.
2. Look at the project without opening every file:
   - Folders with numbered text files (`01-…md`, `Chapter 1.txt`): likely chapters, or one-file-per-scene scripts. Note the naming pattern.
   - `*.fountain` or `*.fdx` files: likely a screenplay.
   - A title page (`Title:` in a Fountain file), a README, or a folder name: likely the title.
   - Character lists, story bibles, outlines, or notes on accepted style choices: possible `context` files.
   - A `.cursor/` folder: they use Cursor.
3. Skim the opening of the first unit or two to guess the protagonist (the point-of-view character, or the name that leads the first scenes).

## 2. Ask

Use the AskUserQuestion tool for the choices, with your detected answer first and marked "(Recommended)". Keep each call to four questions or fewer.

- **Form:** novel, screenplay, teleplay, stage play.
- **Source:** the folders or files you found. If there are several books, scripts or episodes, each becomes a volume; ask which to include.
- **Core genre:** offer the three most likely of Action, Thriller, Horror, Crime, Love, Performance, Society, Status, Worldview, Morality, War, Western, based on what you skimmed. "Other" lets them type one.
- **Extra genre contracts** (multiple choice): progression (LitRPG, cultivation, system stories), mystery (fair-play clues), romance (relationship beats), none.

Then confirm in plain text, in one message: title, protagonist, author name (optional), a one-line description of the lane (optional), comparable titles (optional), and any context files you found. Accept "skip" for anything optional.

## 3. Write and check

1. Write `draftboard.json` following `config.md`. Leave out empty optional fields. Use the default output folders (`draftboard/runs`, `draftboard/briefs`) unless the writer asked for others.
2. Run the script with `check`. It lists the units it found per volume.
   - **No units, or the wrong ones:** fix `source` (usually the `pattern` for file names, or the file path) and run `check` again. Show the writer the first and last few units so they can confirm.
   - **Very short units flagged:** ask whether they are placeholders. They can stay.
3. If they use Cursor, offer to add a Cursor rule so Cursor's agent also sees each unit's brief. If yes, copy `${CLAUDE_PLUGIN_ROOT}/templates/cursor-issues.mdc` to `.cursor/rules/draftboard-issues.mdc`, replacing `{{GLOBS}}` with the source folders as globs (for example `book 1/*.md,book 2/*.md`) and `{{BRIEFS}}` with the briefs folder.
## 4. Hand off

End with the next step, not a question about something else. In a few lines:
- what was set up (title, form, volumes, unit count, total words);
- **the next step is `/draftboard:map`**, which runs several agents over the whole work;
- **what it costs:** it reads the whole work once and then works from notes, so usage scales with length. As a guide, a 170,000-word novel took about 2 million tokens; a feature script or novella takes a fraction of that. Give the estimate for their word count, and say a long novel can use a large share of a session's limits on smaller plans;
- that they can rerun `/draftboard:setup` any time to change settings.

Never edit the manuscript or script.
