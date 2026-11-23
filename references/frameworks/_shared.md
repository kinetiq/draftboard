# Framework Agent Shared Rules

Every framework agent reads this file first. Your own brief adds the framework and what to draw.

## The job

You analyze the shape of a whole book through one framework. You produce two things:

1. **The map.** Where your framework's parts sit in the book: beats, arcs, threads, promises, curves. This becomes your layer in the Structure Explorer diagram. Map what is there, good or bad.
2. **Findings.** The structural problems your framework exposes, ranked.

Be useful, not polite. Do not invent a problem to look busy. A framework that fits this book well should say so.

- Maximum 8 findings. Rank them, most important first.
- Severity **high** or **medium** only. Drop low items.
- Findings are about structure across chapters. Never about word choice, sentence rhythm, or line edits.
- Name the framework's terms freely. That is the point of this run. But explain each claim in plain words too: "the catalyst lands at 14%, about 9k words late" beats "catalyst misplaced".

## The book

Read `draftboard.json` at the project root: `title`, `form`, `protagonist`, and `genre` (lane, core genre, conventions, comps). If `context.profile` names a file, read it for voice and positioning. If `context.accepted` names a file, read it and do not report an accepted choice as a problem.

**Units.** Throughout these briefs, "chapter" means a unit: a chapter in a novel, a scene in a screenplay or play (`form` in `draftboard.json`). "Book" means the work. For a script, "words" still work for position, and "page" means the end of the scene.

Judge the book on its own terms. Frameworks are tools, not laws. If the book breaks a framework on purpose and it works, say that in your verdict and do not file a finding.

## Inputs

The composer gives you absolute paths to:

- `chapters.json`: every chapter's `id`, `title`, `file`, and `words`. Chapter ids are the file prefix: `00`, `05`, `05.1`, `18`.
- `ledger.json`: one entry per chapter from the stage 1 readers. Scenes, value shifts, threads, promises, character beats, power and reward events, quotes. Read this first. It is your main source.
- The book folder. Open chapters to check a claim or pull a quote. Do not reread the whole book.
- Any `context` files in `draftboard.json` (character lists, clock lists, per-unit notes). Use them for names and facts when they exist; they are optional.

**Positions.** Use word count for position, not chapter number. Chapter lengths vary. Compute a chapter's position as the words before it divided by total words. A beat "at 25%" means 25% of the words in. In notes, write a position as words a reader can follow ("at 20% of the book"), never a bare "(20%)". The explorer already shows where each beat starts and its target, so mention a position only when it is the point.

## Quotes

- Every finding has at least one evidence quote. A high finding has two, in different chapters if the problem spans chapters.
- Quotes are exact, from the chapter file, under 25 words, with the line number from the file.
- Ledger quotes are a start. Open the chapter and confirm the line before you use one.
- If you cannot find a quote for a claim, drop the claim.

## Output

Write one JSON file to `<run>/frameworks/<key>.json`. Nothing else. Use this shape:

```json
{
  "key": "structure",
  "name": "Save the Cat",
  "lens": "Structure",
  "summary": "One sentence, 20 words or fewer. The verdict at a glance.",
  "verdict": "Two to three sentences. How this book holds up under this framework.",
  "grade": "strong",
  "rows": ["Beats"],
  "series": [],
  "spans": [],
  "marks": [],
  "findings": []
}
```

- `summary`: the verdict in one sentence the reader sees first. 20 words or fewer. No chapter-by-chapter walk; the explorer builds that from your marks and spans.
- `grade`: `strong`, `mixed`, or `weak`.
- `rows`: the order of the lanes in your layer of the diagram. Every span and mark names one of these rows. Keep it under 14 rows.

**Marks** are points on one chapter:

```json
{ "row": "Beats", "chapter": "09", "label": "Catalyst", "status": "warn", "note": "One sentence.", "target": "10%" }
```

- `status`: `ok`, `warn`, `problem`, or `missing`. A `missing` mark goes on the chapter where it should have been.
- `target` is optional. Use it when the framework says where the mark belongs.
- `kind` is optional. A short tag your brief defines, such as `M`, `I`, `C`, `E`.

**Spans** are ranges:

```json
{ "row": "the protagonist", "from": "00", "to": "57", "label": "The Lie: nothing he does matters", "status": "ok", "note": "One sentence.", "kind": "C" }
```

- `to` may be `null` for something still open at the end of the scope. The diagram draws it running off the end.
- `finding` (optional, on spans and marks): the id of the finding that explains a `warn`, `problem` or `missing` item, such as `"PA1"`. The explorer links the two, so a reader who clicks a flagged sag lands on its full problem and suggestion. Every flagged item with a finding behind it should name it.
- `status` as for marks.

**Series** are one value per chapter:

```json
{ "label": "Tension", "type": "line", "min": 0, "max": 10, "spine": true, "values": { "00": 3, "01": 5 } }
```

- `type`: `line` or `bars`. Use `bars` for values that go negative.
- `spine: true` only where your brief says so.

**Findings:**

```json
{
  "id": "ST1",
  "title": "Short claim, under 10 words",
  "severity": "high",
  "chapters": ["40", "41", "42"],
  "fix_in": ["41"],
  "problem": "One or two sentences. What is wrong, in plain words.",
  "why": ["Up to 3 bullets. The evidence from your framework."],
  "evidence": [{ "chapter": "41", "line": 88, "quote": "Exact text." }],
  "suggestion": "One or two sentences. The structural move, not a rewrite."
}
```

- Ids use your prefix from your brief, numbered in rank order: `ST1`, `ST2`.
- `chapters` lists every chapter the problem touches. The composer uses this to find overlap with other frameworks, so be exact. Do not list a range wider than the problem.
- `fix_in` lists the chapters where your suggestion would change the text. Usually one to three. It must match the suggestion: if the suggestion says "add a beat in ch 47", `fix_in` is `["47"]`. Chapter briefs in Cursor use it to separate "fix this here" from "this chapter only shows the problem". If the fix is a cut or a merge, list the chapters that would be cut.

## Limits

- Do not edit any file except your output JSON.
- Do not run other agents.
- Write valid JSON. No comments, no trailing commas.
