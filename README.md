# Draftboard

**A story doctor for your draft. Diagnoses the structure; never touches the manuscript.**

Draftboard is a plugin for [Claude Code](https://claude.com/claude-code). Point it at a **finished draft**, a novel or a screenplay, and it reads the whole thing through six craft frameworks at once:

| Framework | Asks |
|---|---|
| Save the Cat beat sheet | Are the big beats there, and in the right place? |
| Character arcs (K.M. Weiland) | What does each main character believe, and when does it break? |
| Promises and payoffs (Brandon Sanderson) | What did the story promise, and did it pay? |
| MICE threads (Mary Robinette Kowal) | Do threads close in the right order? |
| Value shifts (Story Grid) | Does every chapter or scene turn something? Where does it sag? |
| Genre contract | Does it deliver what its genre promises? |

Four more are offered when your work fits them: **Openings** (does page one start on the real problem, and does the opening promise the book you wrote?), **Endings** (is the climax won with means the reader already understood, and what is left hanging?), **Theme** (Truby's moral argument) and **Opposition** (Truby's opponent web). Draftboard also charts **cast presence**, who is on the page in each chapter and who goes missing, measured from the readers' notes at no extra cost.

Then it shows you **where the frameworks agree**, because a problem that three frameworks find independently is the one to fix first.

You get:

- **An interactive map of your whole story.** A tension curve with a reference shape, every framework's beats, arcs and threads laid along the same timeline, an overlap view of where they agree, and every finding with its evidence and a suggested fix.
- **A brief for every chapter or scene.** What to fix here, what only shows here, tension, value shifts, threads in play, and a **My notes** section for your own issues that survives every rebuild. Claude sees the brief automatically when you work on that chapter.

It never edits your manuscript. Every finding is a reading through a framework, checked against quotes from your text. You decide what to do with it.

## Install

In Claude Code:

```
/plugin marketplace add kinetiq/draftboard
/plugin install draftboard@draftboard
```

You also need **Python 3.10 or newer** on your PATH (`python`, `python3` or `py`). Draftboard uses only the standard library.

## Use

1. **Set up:** `/draftboard:setup`. It looks at your project, asks a few questions (form, which files, protagonist, genre), and writes `draftboard.json`. A few minutes.
2. **Map the draft:** `/draftboard:map`. Several agents read the whole work in parallel (a 170k-word novel uses about eleven).
3. **Work chapter by chapter:** ask "what issues am I in?" while working on a chapter or scene (`/draftboard:issues`), or say "add a note to this chapter: …".
4. **Close issues as you fix them:** say "AR3 is fixed" or "I'm keeping ST2". Claude checks the current text, quotes the line that fixes it, and marks it. Closed findings drop off the map and out of the briefs, and the next run tells you if one comes back.

## How much it uses

Each run starts about eight to eleven agents. Most of the cost is reading your text, so it grows with length. As a guide:

| Work | Tokens, roughly |
|---|---|
| A short script or story | 350,000 |
| A feature screenplay (about 25,000 words) | 530,000 |
| A 90,000-word novel | 1,000,000 |
| A 170,000-word novel | 1,600,000 |

On larger plans that is comfortable; on smaller plans a long novel can use a big share of your limits, so run it when you won't need Claude for a while. Draftboard tells you its estimate and asks before it starts.

**Use a capable model.** The analysis is careful reading and judgment; the latest Opus at medium effort works well.

## What it reads

| Your project | In `draftboard.json` |
|---|---|
| A folder of chapter files (`01-Title.md`, `Chapter 12.txt`) | `"source": { "type": "files", "dir": "manuscript" }` |
| A Fountain screenplay | `"source": { "type": "fountain", "file": "script.fountain" }` |
| A Final Draft file | `"source": { "type": "fdx", "file": "script.fdx" }` |
| One file per scene | `"type": "files"` with that folder |

Several books, scripts or episodes can live in one project as separate volumes. Setup handles all of this; [references/config.md](references/config.md) has the details.

## Using Cursor too

If your project has a `.cursor/` folder, setup offers to add a Cursor rule, so Cursor's agent also reads each chapter's brief when you work on it.

## How it works

- **Readers** read the draft once, in parallel chunks, and write a shared ledger: scenes and their value shifts, threads, promises, character beats, quotes with line numbers.
- **One tension agent** scores every chapter or scene on a fixed 0–10 scale, both the last page and the peak, so the scale is consistent across the whole work.
- **Six framework agents** each read the ledger through their framework and file findings, with evidence quotes and where the fix belongs.
- **The composer** (your Claude Code session) checks every important quote against your text, drops what doesn't hold, groups findings that share a cause, and builds the map and the briefs.

The analysis lives in your project (`draftboard/` by default), so you can commit it, compare runs, and keep your notes with your draft.

## License

Draftboard is source-available under the [PolyForm Shield License 1.0.0](LICENSE.md).

In plain words:

- **Use it for anything, including your professional writing.** Analyze books and scripts you sell, use it for clients, change it for your own needs.
- **Don't build a competing product with it.** You may not ship Draftboard, or a product built on it, that competes with Draftboard: for example a writing app, AI service, or plugin that offers its analysis as a feature.

The license text is the binding version; this summary is just a guide.
