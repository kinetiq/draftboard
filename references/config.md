# draftboard.json

Every project has one `draftboard.json` at its root. The `setup` skill writes it by asking questions; people can also edit it by hand. Every other part of Draftboard reads it.

## Example: a novel

```json
{
  "title": "Death to False Gods",
  "author": "Lincoln Hart",
  "form": "novel",
  "protagonist": "Liam",
  "volumes": [
    {
      "key": "book-1",
      "label": "Book 1",
      "source": { "type": "files", "dir": "book 1", "pattern": "^(\\d{2}(?:\\.\\d+)?)-(.+)\\.md$" }
    }
  ],
  "labels": { "00": "Prologue" },
  "genre": {
    "lane": "Character-driven space opera with LitRPG system elements",
    "core": "Action",
    "conventions": ["progression"],
    "comps": ["Dungeon Crawler Carl", "Murderbot", "The Expanse"]
  },
  "context": {
    "profile": ".cursor/rules/critics/_shared.mdc",
    "accepted": ".cursor/critiques/accepted.md",
    "characters": "ai.bible/characters/index.md",
    "clocks": "ai.bible/ticking-clocks.md",
    "unit_notes": "ai.bible/chapters/{volume_number}"
  },
  "output": { "runs": "book-analysis/frameworks", "briefs": "book-analysis/briefs" }
}
```

## Example: a screenplay

```json
{
  "title": "Night Ferry",
  "author": "Sam Okafor",
  "form": "screenplay",
  "protagonist": "Dee",
  "volumes": [
    { "key": "script", "label": "Draft 3", "source": { "type": "fountain", "file": "night-ferry.fountain" } }
  ],
  "genre": { "lane": "Contained thriller", "core": "Thriller", "conventions": [], "comps": ["Hell or High Water", "Locke"] }
}
```

## Fields

| Field | Required | Meaning |
|---|---|---|
| `title` | yes | The work's title. Shown on the explorer. |
| `author` | no | Shown on the explorer. |
| `form` | yes | `novel`, `screenplay`, `teleplay`, `stage play`, or `other`. Sets the words agents use (chapter or scene, page or word). |
| `protagonist` | yes | The main point-of-view character. Value shifts and tension are scored from their side. |
| `volumes` | yes | One entry per book, script, or episode to analyze. Each run covers one volume. |
| `volumes[].key` | yes | Short id with no spaces, such as `book-1` or `script`. Names folders. |
| `volumes[].label` | yes | Display name, such as `Book 1` or `Draft 3`. |
| `volumes[].source` | yes | Where the text is. See Sources. |
| `labels` | no | Display names for unit ids, such as `{ "00": "Prologue" }`. |
| `genre.lane` | no | One line describing the work's lane. |
| `genre.core` | no | The Story Grid core genre: Action, Horror, Thriller, Crime, Love, Performance, Society, Status, Worldview, Morality, War, or Western. The genre agent picks one if empty. |
| `genre.conventions` | no | Extra reader contracts to check, such as `progression` (LitRPG or cultivation), `mystery` (fair-play clues), `romance` (relationship beats). |
| `genre.comps` | no | Comparable titles. |
| `context.*` | no | Optional project files agents may read: a voice or profile note, a list of accepted choices not to flag, character and clock lists, and per-unit summaries. `{volume_number}` is replaced by the digits in the volume key. |
| `output.runs` | no | Where runs are saved. Default `draftboard/runs`. |
| `output.briefs` | no | Where the current briefs live. Default `draftboard/briefs`. |

## Sources

A **unit** is what gets one entry on the map: a chapter in a novel, a scene in a script.

| `type` | Fields | Units |
|---|---|---|
| `files` | `dir`, `pattern` | One file per unit. `pattern` is a regular expression on the file name: group 1 is the unit id, group 2 (optional) the title. Default pattern: `^(\d+(?:\.\d+)?)[-_ ]+(.+)\.(md|txt|fountain)$`. Works for chapters and for one-file-per-scene scripts. |
| `fountain` | `file` | One Fountain screenplay. Each scene heading (`INT.`, `EXT.`, `INT./EXT.`, `I/E`, or a forced `.HEADING`) starts a unit. Ids are `001`, `002`… unless the script numbers its scenes (`#12#`). |
| `fdx` | `file` | One Final Draft file. Converted to Fountain text in the run folder, then split like `fountain`. |

Evidence line numbers always point into the file an agent can open: the chapter file, the Fountain script, or the converted Fountain copy of an FDX file.
