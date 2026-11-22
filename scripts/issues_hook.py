#!/usr/bin/env python3
"""
Draftboard PostToolUse hook. When Claude reads or edits a chapter (or a one-file
scene) that has a Draftboard brief, hand Claude that unit's notes and issues.

Shows each unit once per session. Never fails the tool call: any problem means no output.
Single-file scripts (Fountain, FDX) are skipped; ask the issues skill about a scene instead.
"""

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from units import DEFAULT_PATTERN  # noqa: E402


def find_project(start: Path) -> Path | None:
    for folder in [start, *start.parents]:
        if (folder / "draftboard.json").exists():
            return folder
    return None


def section(text: str, heading: str) -> list[str]:
    out, inside = [], False
    for line in text.splitlines():
        if line.startswith("## "):
            inside = line[3:].startswith(heading)
            continue
        if inside:
            out.append(line)
    return out


def main() -> None:
    data = json.load(sys.stdin)
    path = (data.get("tool_input") or {}).get("file_path") or ""
    if not path:
        return
    p = Path(path).resolve()
    project = find_project(p.parent) or find_project(Path(data.get("cwd") or ".").resolve())
    if not project:
        return
    cfg = json.loads((project / "draftboard.json").read_text(encoding="utf-8"))

    match = None
    for vol in cfg.get("volumes", []):
        src = vol.get("source", {})
        if src.get("type", "files") != "files":
            continue
        if p.parent != (project / src.get("dir", "")).resolve():
            continue
        m = re.match(src.get("pattern") or DEFAULT_PATTERN, p.name)
        if m:
            match = (vol, m.group(1))
            break
    if not match:
        return
    vol, uid = match

    seen_file = Path(tempfile.gettempdir()) / f"draftboard-issues-{data.get('session_id', 'none')}.json"
    seen = set(json.loads(seen_file.read_text())) if seen_file.exists() else set()
    key = f"{project}|{vol['key']}|{uid}"
    if key in seen:
        return

    out = cfg.get("output", {})
    brief = project / out.get("briefs", "draftboard/briefs") / vol["key"].replace(" ", "-") / f"{uid}.md"
    if not brief.exists():
        return
    latest_path = project / out.get("runs", "draftboard/runs") / "latest.json"
    entry = (json.loads(latest_path.read_text(encoding="utf-8")).get(vol["key"]) if latest_path.exists() else None) or {}
    text = brief.read_text(encoding="utf-8")

    mine = []
    if "<!-- my-notes:start -->" in text:
        block = text.split("<!-- my-notes:start -->", 1)[1].split("<!-- my-notes:end -->", 1)[0]
        mine = [l.strip() for l in block.splitlines() if l.strip()]
    fixes = [l[4:] for l in section(text, "Fix here") if l.startswith("### ")]
    shows = [l[2:] for l in section(text, "Shows here") if l.startswith("- ")]
    tension = next((l for l in text.splitlines() if l.startswith("Tension **")), "").replace("**", "")

    changed = ""
    if entry.get("git"):
        try:
            rel = p.relative_to(project).as_posix()
            diff = subprocess.run(["git", "diff", "--stat", entry["git"], "--", rel],
                                  cwd=project, capture_output=True, text=True, timeout=5).stdout.strip()
            if diff:
                changed = f"This file has changed since the analysis (git {entry['git']}); check these against the current text before relying on them."
        except Exception:
            pass

    lines = [f"Draftboard notes for {vol.get('label', vol['key'])} {uid} (run {entry.get('run', '?')}). Full brief: {brief.relative_to(project).as_posix()}"]
    if changed:
        lines.append(changed)
    if tension:
        lines.append(tension)
    if mine:
        lines.append("The author's own notes (treat these first): " + " ".join(mine))
    lines.append("Fix here: " + ("; ".join(fixes) if fixes else "nothing"))
    if shows:
        lines.append("Shows here, fix elsewhere: " + "; ".join(shows))
    lines.append("Use the draftboard issues skill for how to use these. Mention the fix-here items briefly when relevant; never edit the manuscript because of them.")

    seen.add(key)
    seen_file.write_text(json.dumps(sorted(seen)))
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PostToolUse", "additionalContext": "\n".join(lines)}}))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
