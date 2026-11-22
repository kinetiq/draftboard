"""
Finding the units of a work (chapters, scenes) from draftboard.json, and measuring them.

Sources:
  files     one file per unit, matched by a regular expression on the file name
  fountain  one Fountain screenplay, split at scene headings
  fdx       one Final Draft file, converted to Fountain text, then split
"""

import re
import xml.etree.ElementTree as ET
from pathlib import Path

DEFAULT_PATTERN = r"^(\d+(?:\.\d+)?)[-_ ]+(.+)\.(md|txt|fountain)$"
SCENE_HEADING = re.compile(r"^(?:(?:INT|EXT|EST|INT\./EXT|INT/EXT|I/E)[\. ]|\.(?=[A-Za-z0-9]))", re.IGNORECASE)
SCENE_NUMBER = re.compile(r"#([\w.\-]+)#\s*$")
CHARACTER_CUE = re.compile(r"^[@]?[A-Z0-9][A-Z0-9 .'\-]*(\s*\([^)]*\))?\s*\^?$")
PROSE_DIALOGUE = re.compile(r'“[^”\n]*”|"[^"\n]*"')


def sort_key(unit_id: str) -> tuple:
    return tuple(int(p) if p.isdigit() else p for p in re.split(r"[.\-]", unit_id))


# ---------- files ----------

def unit_note_title(project: Path, cfg: dict, volume: dict, unit_id: str) -> str | None:
    """Optional: a title from a per-unit summary file whose first line reads '...: Title'."""
    pattern = (cfg.get("context") or {}).get("unit_notes")
    if not pattern:
        return None
    digits = re.search(r"(\d+)", volume["key"])
    folder = project / pattern.replace("{volume_number}", digits.group(1) if digits else "").replace("{volume}", volume["key"])
    if not folder.is_dir():
        return None
    for note in folder.glob(f"{unit_id}-*.md"):
        first = note.read_text(encoding="utf-8").splitlines()[:1]
        if first and ":" in first[0]:
            return first[0].split(":", 1)[1].strip()
    return None


def files_units(project: Path, cfg: dict, volume: dict) -> list[dict]:
    src = volume["source"]
    folder = project / src["dir"]
    if not folder.is_dir():
        raise SystemExit(f"No such folder: {folder}")
    pattern = re.compile(src.get("pattern") or DEFAULT_PATTERN)
    units = []
    for path in folder.iterdir():
        m = pattern.match(path.name)
        if not m or not path.is_file():
            continue
        uid = m.group(1)
        slug = m.group(2) if m.re.groups >= 2 and m.group(2) else path.stem
        title = unit_note_title(project, cfg, volume, uid) or re.sub(r"[-_]+", " ", slug).strip()
        text = path.read_text(encoding="utf-8")
        units.append({"id": uid, "title": title, "file": path.relative_to(project).as_posix(),
                      "words": len(text.split()), "lines": len(text.splitlines())})
    units.sort(key=lambda u: sort_key(u["id"]))
    return units


# ---------- fountain ----------

def is_scene_heading(line: str, prev_blank: bool) -> bool:
    s = line.strip()
    if not s or not prev_blank:
        return False
    if s.startswith("..") :
        return False
    return bool(SCENE_HEADING.match(s))


def fountain_units(project: Path, fountain_path: Path, rel_file: str) -> list[dict]:
    lines = fountain_path.read_text(encoding="utf-8").splitlines()
    starts = []
    prev_blank = True
    for i, line in enumerate(lines):
        if is_scene_heading(line, prev_blank):
            starts.append(i)
        prev_blank = not line.strip()
    if not starts:
        raise SystemExit(f"No scene headings found in {fountain_path}. Fountain scene headings start with INT. or EXT.")
    units = []
    for n, start in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        heading = lines[start].strip().lstrip(".")
        num = SCENE_NUMBER.search(heading)
        uid = num.group(1) if num else f"{n + 1:03d}"
        heading = SCENE_NUMBER.sub("", heading).strip()
        body = lines[start:end]
        units.append({"id": uid, "title": heading, "file": rel_file, "start": start + 1, "end": end,
                      "words": len(" ".join(body).split()), "lines": end - start})
    return units


# ---------- fdx ----------

FDX_TYPES = {"Scene Heading": "heading", "Action": "action", "Character": "character", "Parenthetical": "paren",
             "Dialogue": "dialogue", "Transition": "transition", "Shot": "action", "General": "action"}


def fdx_to_fountain(fdx_path: Path) -> str:
    root = ET.parse(fdx_path).getroot()
    out = []
    for p in root.iter("Paragraph"):
        kind = FDX_TYPES.get(p.get("Type", "Action"), "action")
        text = "".join(t.text or "" for t in p.iter("Text")).strip()
        if not text:
            continue
        number = p.get("Number")
        if kind == "heading":
            heading = text.upper()
            if not SCENE_HEADING.match(heading):
                heading = "." + heading
            out += ["", heading + (f" #{number}#" if number else ""), ""]
        elif kind == "character":
            out += ["", text.upper()]
        elif kind == "paren":
            out.append(text if text.startswith("(") else f"({text})")
        elif kind == "dialogue":
            out.append(text)
        elif kind == "transition":
            out += ["", f"> {text.upper()}", ""]
        else:
            out += ["", text, ""]
    cleaned, blank = [], False
    for line in out:
        if not line.strip():
            if not blank and cleaned:
                cleaned.append("")
            blank = True
        else:
            cleaned.append(line)
            blank = False
    return "\n".join(cleaned).strip() + "\n"


# ---------- dispatch ----------

def rel_or_abs(project: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(project.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def list_units(project: Path, cfg: dict, volume: dict, run: Path | None = None) -> list[dict]:
    src = volume["source"]
    kind = src.get("type", "files")
    if kind == "files":
        return files_units(project, cfg, volume)
    path = project / src["file"]
    if not path.exists():
        raise SystemExit(f"No such file: {path}")
    if kind == "fountain":
        return fountain_units(project, path, rel_or_abs(project, path))
    if kind == "fdx":
        target_dir = (run or project / "draftboard") / "source"
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / (path.stem + ".fountain")
        target.write_text(fdx_to_fountain(path), encoding="utf-8")
        return fountain_units(project, target, rel_or_abs(project, target))
    raise SystemExit(f"Unknown source type {kind!r}. Use files, fountain or fdx.")


def unit_text(project: Path, unit: dict) -> str:
    path = Path(unit["file"]) if Path(unit["file"]).is_absolute() else project / unit["file"]
    if not path.exists():
        return ""
    lines = path.read_text(encoding="utf-8").splitlines()
    if unit.get("start"):
        lines = lines[unit["start"] - 1:unit.get("end", len(lines))]
    return "\n".join(lines)


def screenplay_dialogue(lines: list[str]) -> int:
    """Words in dialogue blocks: the lines under a character cue, up to the next blank line."""
    words, in_dialogue, prev_blank = 0, False, True
    for line in lines:
        s = line.strip()
        if not s:
            in_dialogue, prev_blank = False, True
            continue
        if in_dialogue and not (s.startswith("(") and s.endswith(")")):
            words += len(s.split())
        elif prev_blank and CHARACTER_CUE.match(s) and not SCENE_HEADING.match(s) and any(c.isalpha() for c in s):
            in_dialogue = True
        prev_blank = False
    return words


def text_metrics(project: Path, unit: dict, screenplay: bool) -> dict:
    """Measured from the text, not judged: dialogue share and sentence length."""
    text = unit_text(project, unit)
    words = len(text.split())
    if words < (15 if screenplay else 200):
        return {}
    if screenplay:
        spoken = screenplay_dialogue(text.splitlines())
    else:
        spoken = sum(len(m.split()) for m in PROSE_DIALOGUE.findall(text))
    sentences = [s for s in re.split(r"(?<=[.!?])[\"”’)]*\s+", text) if s.strip()]
    return {"dialogue": round(100 * spoken / words, 1), "sentence": round(words / max(1, len(sentences)), 1)}
