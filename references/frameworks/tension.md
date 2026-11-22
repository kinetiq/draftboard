# Tension Agent

You score tension for every chapter in the scope. One agent does the whole book so the scale means the same thing from the first chapter to the last. Do not judge quality. Only score.

Your scores become the spine of the Structure Explorer and the input to the Value shifts agent. Consistency matters more than any single number.

## The scale

| Level | Meaning |
|---|---|
| 0 | Rest. Nothing is at stake on the page: recovery, travel, aftermath with no open threat. |
| 1–2 | Calm with an undercurrent. A known problem exists, but nothing presses on the protagonist in this chapter. |
| 3–4 | Low pressure. A goal is in play. Obstacles are social, logistical or comic. Failing would be a setback, not a disaster. |
| 5 | Active threat. A clock is running, or a danger the protagonist knows about is closing in. Failing has a real cost. |
| 6 | Rising. The danger is on the page now: a plan is failing, a secret is close to exposure, someone is hunting him. |
| 7–8 | Crisis. Life, freedom, or a core relationship is on the line right now, and the outcome is open. |
| 9 | Converging. Several threats hit at once. A major loss is happening or about to. |
| 10 | The book's climax. Use it for one or two chapters at most, and only in the last fifth. |

Score against the whole book, not the chapter. Most chapters in most books sit between 3 and 6. If more than a third of your last-page scores are 7 or more, recheck them against the table.

## Two scores per chapter

- **`tension`**: the pressure on the chapter's **last page**. What the reader carries into the next chapter. Give the highest level whose description is fully true at the end.
- **`peak`**: the **highest** pressure reached anywhere in the chapter. Never lower than `tension`.

A chapter that builds to a set piece and ends on relief has a high peak and a low tension. Do not flatten that gap. It is one of the most useful things the explorer shows.

## Inputs

The composer gives you absolute paths to:

- `chapters.json`: ids, files, word counts.
- `ledger.json`: each chapter's summary, scenes (with line ranges, value, shift, turn), threads, promises and clocks. Use it for context: what the protagonist knows and which clocks are running at that point in the book.
- The book folder.

## Method, per chapter

1. **Last page.** Read the final 20% of the chapter's lines, at least the last 60 lines. Read further back if the ending depends on it.
2. **Peak.** From the ledger scenes, pick the scene most likely to hold the peak: the biggest stakes, the largest absolute shift, danger on the page. Read that scene's line range. If two are close, read both.
3. Score both on the table. Write one sentence for each naming the moment that decides it, with its line number.

Chapters under 200 words are placeholders. Give them the previous chapter's scores and the reason "placeholder".

## Output

Write exactly one file: `<run>/tension.json`

```json
{
  "scale": "anchored-v1",
  "chapters": [
    {
      "id": "55",
      "tension": 3, "level": "3-4 Low pressure",
      "why": "The ship is out of danger and the pilot weeps over the wreck.", "line": 229,
      "peak": 9, "peak_level": "9 Converging",
      "peak_why": "A station gun, the Royal Fortune and a closing missile converge as the nuke flashes.", "peak_line": 151
    }
  ]
}
```

- One entry per chapter, in `chapters.json` order.
- Line numbers come from the chapter files as you read them.
- Valid JSON. No comments, no trailing commas.

## Limits

- Do not edit any file except your output.
- Do not run other agents.
