#!/usr/bin/env python3
"""
Draftboard: a story doctor for your draft. Diagnoses the structure; never touches the manuscript.

Usage (run from anywhere inside a project that has a draftboard.json):
    python draftboard.py check
    python draftboard.py units [--volume KEY] [--run FOLDER] [--groups N]
    python draftboard.py ledger RUN
    python draftboard.py build RUN
    python draftboard.py sample [--volume KEY]

check   Reads draftboard.json, finds the units (chapters or scenes) and reports what it found.
units   Writes RUN/chapters.json for one volume and prints reading groups balanced by words.
ledger  Joins RUN/ledger/*.json into RUN/ledger.json and lists names that look like duplicates.
build   Merges the run into analysis.json, checks it, writes explorer.html and the unit briefs.
sample  For developing Draftboard: builds an explorer with placeholder findings over the
        real unit list, to test the page. Not part of the writer-facing flow.
"""

import argparse
import difflib
import html
import json
import math
import random
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import units as U  # noqa: E402

PLUGIN_ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = PLUGIN_ROOT / "templates" / "explorer.html"
PLACEHOLDER = "/*ANALYSIS_JSON*/"
STATUSES = {"ok", "warn", "problem", "missing"}
SEVERITIES = {"high", "medium"}
GRADES = {"strong", "mixed", "weak"}
FRAMEWORK_ORDER = ["structure", "arcs", "promises", "mice", "pacing", "genre", "theme", "opposition"]
SCREEN_FORMS = {"screenplay", "teleplay", "stage play"}

PROJECT_ROOT: Path = Path.cwd()
CFG: dict = {}
sort_key = U.sort_key


# ---------- config ----------

def find_project(start: Path) -> Path:
    for folder in [start, *start.parents]:
        if (folder / "draftboard.json").exists():
            return folder
    raise SystemExit("No draftboard.json found here or in any parent folder. Run the Draftboard setup first (/draftboard:setup).")


def load_config(project: Path) -> dict:
    cfg = json.loads((project / "draftboard.json").read_text(encoding="utf-8"))
    for field in ("title", "form", "protagonist", "volumes"):
        if not cfg.get(field):
            raise SystemExit(f"draftboard.json: missing {field!r}")
    for v in cfg["volumes"]:
        for field in ("key", "label", "source"):
            if not v.get(field):
                raise SystemExit(f"draftboard.json: a volume is missing {field!r}")
    out = cfg.setdefault("output", {})
    out.setdefault("runs", "draftboard/runs")
    out.setdefault("briefs", "draftboard/briefs")
    cfg.setdefault("labels", {})
    cfg.setdefault("genre", {})
    cfg.setdefault("context", {})
    return cfg


def volume_for(key: str | None) -> dict:
    vols = CFG["volumes"]
    if not key:
        return vols[0]
    for v in vols:
        if v["key"] == key:
            return v
    raise SystemExit(f"No volume {key!r} in draftboard.json. Volumes: {', '.join(v['key'] for v in vols)}")


def is_screen() -> bool:
    return CFG.get("form") in SCREEN_FORMS


def unit_noun() -> str:
    return "scene" if is_screen() else "chapter"


def unit_short() -> str:
    return "Sc" if is_screen() else "Ch"


def runs_dir() -> Path:
    return PROJECT_ROOT / CFG["output"]["runs"]


def briefs_dir() -> Path:
    return PROJECT_ROOT / CFG["output"]["briefs"]


# ---------- units ----------

def balanced_groups(units: list[dict], count: int) -> list[list[dict]]:
    total = sum(c["words"] for c in units)
    target = total / max(count, 1)
    groups, current, words = [], [], 0
    for unit in units:
        current.append(unit)
        words += unit["words"]
        if words >= target * (len(groups) + 1) and len(groups) < count - 1:
            groups.append(current)
            current = []
    if current:
        groups.append(current)
    return groups


def git(*args: str) -> str:
    try:
        return subprocess.run(["git", *args], cwd=PROJECT_ROOT, capture_output=True, text=True, timeout=10).stdout.strip()
    except Exception:
        return ""


def source_path(volume: dict) -> str:
    src = volume["source"]
    return src.get("dir") or src.get("file") or "."


def cmd_check(args) -> int:
    print(f"{CFG['title']} · {CFG['form']} · protagonist {CFG['protagonist']}")
    print(f"runs -> {CFG['output']['runs']}   briefs -> {CFG['output']['briefs']}")
    for v in CFG["volumes"]:
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            units = U.list_units(PROJECT_ROOT, CFG, v, Path(tmp))
        words = sum(u["words"] for u in units)
        print(f"\n{v['label']} ({v['key']}): {len(units)} {unit_noun()}s, {words:,} words, from {source_path(v)}")
        show = units if len(units) <= 8 else units[:4] + [None] + units[-3:]
        for u in show:
            print("    ..." if u is None else f"    {u['id']:>6}  {u['title'][:60]}  ({u['words']:,} words)")
        tiny = [u["id"] for u in units if u["words"] < (8 if is_screen() else 40)]
        if tiny:
            print(f"    note: very short units (placeholders?): {', '.join(tiny)}")
    for name, rel in (CFG.get("context") or {}).items():
        if rel and "{" not in rel and not (PROJECT_ROOT / rel).exists():
            print(f"warning: context.{name} points to {rel}, which does not exist")
    return 0


def cmd_units(args) -> int:
    volume = volume_for(args.volume)
    stamp = datetime.now().strftime("%Y-%m-%d-%H%M")
    run = Path(args.run).resolve() if args.run else runs_dir() / f"{stamp}-{volume['key']}"
    run.mkdir(parents=True, exist_ok=True)
    units = U.list_units(PROJECT_ROOT, CFG, volume, run)
    sha = git("rev-parse", "--short", "HEAD")
    dirty = git("status", "--porcelain", "--", source_path(volume))
    data = {
        "book": volume["key"],
        "volume": volume["label"],
        "form": CFG["form"],
        "unit": unit_noun(),
        "git": sha,
        "dirty": bool(dirty),
        "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "chapters": units,
    }
    (run / "chapters.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    total = sum(c["words"] for c in units)
    print(f"run folder: {run}")
    print(f"{len(units)} {unit_noun()}s, {total:,} words -> {run / 'chapters.json'}")
    print(f"git {sha or '(not a git repository)'}{' (source has uncommitted changes)' if dirty else ''}")
    groups = args.groups or max(1, min(6, round(total / 43000)))
    for i, group in enumerate(balanced_groups(units, groups), 1):
        words = sum(c["words"] for c in group)
        print(f"g{i}: {group[0]['id']}-{group[-1]['id']}  {len(group)} {unit_noun()}s  {words:,} words")
        for c in group:
            where = f" lines {c['start']}-{c['end']}" if c.get("start") else ""
            print(f"    {c['id']}  {PROJECT_ROOT / c['file']}{where}")
    return 0


# ---------- ledger ----------

def load_json(path: Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        raise SystemExit(f"Bad JSON in {path}: {e}")


def near_duplicates(names: set[str]) -> list[tuple[str, str]]:
    pairs = []
    items = sorted(names)
    for i, a in enumerate(items):
        for b in items[i + 1:]:
            if a.casefold() == b.casefold() or difflib.SequenceMatcher(None, a.casefold(), b.casefold()).ratio() > 0.82:
                pairs.append((a, b))
    return pairs


def cmd_ledger(args) -> int:
    run = Path(args.run).resolve()
    chapters = load_json(run / "chapters.json")["chapters"]
    entries = {}
    for path in sorted((run / "ledger").glob("*.json")):
        for entry in load_json(path).get("chapters", []):
            entries[entry["id"]] = entry
    missing = [c["id"] for c in chapters if c["id"] not in entries]
    ordered = [entries[c["id"]] for c in chapters if c["id"] in entries]
    (run / "ledger.json").write_text(json.dumps({"chapters": ordered}, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"{len(ordered)} of {len(chapters)} chapters -> {run / 'ledger.json'}")
    if missing:
        print("MISSING chapters: " + ", ".join(missing))
    for field in ("threads", "promises"):
        names = {item["name"] for e in ordered for item in e.get(field, []) if item.get("name")}
        pairs = near_duplicates(names)
        if pairs:
            print(f"\n{field}: names that may be the same")
            for a, b in pairs:
                print(f"    {a!r}  ~  {b!r}")
    return 1 if missing else 0


# ---------- build ----------

def apply_tension(run: Path, frameworks: list[dict]) -> None:
    """Put the tension agent's scores into the pacing layer as the map's spine and peak overlay."""
    path = run / "tension.json"
    if not path.exists():
        return
    data = load_json(path)
    rows = data.get("chapters", [])
    tension = {r["id"]: r["tension"] for r in rows if r.get("tension") is not None}
    peak = {r["id"]: max(r.get("peak", r["tension"]), r["tension"]) for r in rows if r.get("tension") is not None}
    scale = data.get("scale", "anchored-v1")
    pacing = next((f for f in frameworks if f.get("key") == "pacing"), None)
    if pacing is None:
        pacing = {"key": "pacing", "name": "Tension", "lens": "Tension agent", "summary": "Tension scored by the tension agent.",
                  "verdict": "Only the tension curve was scored in this run.", "grade": "mixed",
                  "rows": [], "series": [], "spans": [], "marks": [], "findings": []}
        frameworks.append(pacing)
    keep = [s for s in pacing.get("series", []) if not s.get("spine") and s.get("overlay") != "spine"
            and s.get("label") not in ("Tension", "Peak tension")]
    pacing["series"] = [
        {"label": "Tension", "type": "line", "min": 0, "max": 10, "spine": True, "scale": scale,
         "values": tension, "notes": {r["id"]: r.get("why", "") for r in rows}},
        {"label": "Peak tension", "type": "line", "min": 0, "max": 10, "overlay": "spine", "scale": scale,
         "values": peak, "notes": {r["id"]: r.get("peak_why", "") for r in rows}},
    ] + keep


def merge(run: Path) -> dict:
    chapters_data = load_json(run / "chapters.json")
    frameworks = []
    for path in (run / "frameworks").glob("*.json"):
        frameworks.append(load_json(path))
    frameworks.sort(key=lambda f: FRAMEWORK_ORDER.index(f["key"]) if f.get("key") in FRAMEWORK_ORDER else 99)
    apply_tension(run, frameworks)
    composer_path = run / "composer.json"
    composer = load_json(composer_path) if composer_path.exists() else {}
    acts = composer.get("acts")
    if not acts:
        acts = next((f.get("acts") for f in frameworks if f.get("acts")), [])
    for c in chapters_data["chapters"]:
        c.update(U.text_metrics(PROJECT_ROOT, c, is_screen()))
    ledger_path = run / "ledger.json"
    if ledger_path.exists():
        notes = {e["id"]: e for e in load_json(ledger_path).get("chapters", [])}
        for c in chapters_data["chapters"]:
            entry = notes.get(c["id"], {})
            for field in ("summary", "pov"):
                if entry.get(field):
                    c[field] = entry[field]
            if entry.get("scenes"):
                c["scenes"] = [{k: s.get(k) for k in ("value", "shift", "goal", "turn", "line")}
                               for s in entry["scenes"]]
    book = chapters_data.get("book", "")
    analysis = {
        "meta": {
            "title": CFG["title"],
            "author": CFG.get("author", ""),
            "volume": chapters_data.get("volume") or volume_for(book).get("label", book),
            "book": book,
            "form": CFG["form"],
            "unit": unit_noun(),
            "unit_short": unit_short(),
            "protagonist": CFG["protagonist"],
            "labels": CFG.get("labels", {}),
            "run": run.name,
            "git": chapters_data.get("git", ""),
            "dirty": chapters_data.get("dirty", False),
            "created": chapters_data.get("created", ""),
            "sample": composer.get("sample", False),
        },
        "headline": composer.get("headline", ""),
        "acts": acts,
        "chapters": chapters_data["chapters"],
        "frameworks": frameworks,
        "convergence": composer.get("convergence", []),
    }
    apply_status(analysis)
    return analysis


def validate(analysis: dict) -> tuple[list[str], list[str]]:
    errors, warnings = [], []
    ids = {c["id"] for c in analysis["chapters"]}
    finding_ids = set()

    def chapter(ref, where):
        if ref is None:
            return
        if ref not in ids:
            errors.append(f"{where}: unknown chapter {ref!r}")

    for act in analysis.get("acts", []):
        chapter(act.get("from"), f"acts {act.get('label')}")
        chapter(act.get("to"), f"acts {act.get('label')}")

    for fw in analysis["frameworks"]:
        key = fw.get("key", "?")
        for field in ("key", "name", "verdict"):
            if not fw.get(field):
                errors.append(f"{key}: missing {field}")
        if not fw.get("summary"):
            warnings.append(f"{key}: no summary; the explorer will use the verdict's first sentence")
        elif len(fw["summary"].split()) > 24:
            warnings.append(f"{key}: summary is {len(fw['summary'].split())} words; aim for 20 or fewer")
        if fw.get("grade") not in GRADES:
            warnings.append(f"{key}: grade {fw.get('grade')!r} is not strong, mixed or weak")
        rows = fw.setdefault("rows", [])
        for kind in ("spans", "marks"):
            for i, item in enumerate(fw.get(kind, [])):
                where = f"{key}.{kind}[{i}] {item.get('label', '')!r}"
                if kind == "spans":
                    chapter(item.get("from"), where)
                    chapter(item.get("to"), where)
                    if item.get("from") in ids and item.get("to") in ids and \
                            sort_key(item["from"]) > sort_key(item["to"]):
                        errors.append(f"{where}: from {item['from']} is after to {item['to']}")
                else:
                    chapter(item.get("chapter"), where)
                if item.get("status", "ok") not in STATUSES:
                    errors.append(f"{where}: status {item.get('status')!r}")
                row = item.get("row")
                if not row:
                    errors.append(f"{where}: no row")
                elif row not in rows:
                    rows.append(row)
                    warnings.append(f"{key}: row {row!r} was not in rows, added at the end")
        for s in fw.get("series", []):
            for ref in s.get("values", {}):
                chapter(ref, f"{key}.series {s.get('label')!r}")
        for f in fw.get("findings", []):
            fid = f.get("id", "?")
            if fid in finding_ids:
                errors.append(f"{key}: duplicate finding id {fid}")
            finding_ids.add(fid)
            if f.get("severity") not in SEVERITIES:
                errors.append(f"{fid}: severity {f.get('severity')!r}")
            if not f.get("chapters"):
                errors.append(f"{fid}: no chapters")
            for ref in f.get("chapters", []):
                chapter(ref, fid)
            if not f.get("fix_in"):
                warnings.append(f"{fid}: no fix_in; chapter briefs cannot say where to fix it")
            for ref in f.get("fix_in", []):
                chapter(ref, f"{fid} fix_in")
            if not f.get("evidence"):
                warnings.append(f"{fid}: no evidence quotes")
            for e in f.get("evidence", []):
                chapter(e.get("chapter"), f"{fid} evidence")

    spines = [s for fw in analysis["frameworks"] for s in fw.get("series", []) if s.get("spine")]
    if len(spines) > 1:
        warnings.append("more than one spine series; the first is used")
    if not spines:
        warnings.append("no spine series; the diagram has no tension curve")

    for c in analysis.get("convergence", []):
        cid = c.get("id", "?")
        for ref in c.get("chapters", []) + c.get("fix_in", []):
            chapter(ref, cid)
        for fid in c.get("findings", []):
            if fid not in finding_ids:
                errors.append(f"{cid}: unknown finding {fid}")
    return errors, warnings


def page_title(meta: dict) -> str:
    """Draftboard: <title, or its initials if several words> [<volume>] <Mon-Day of the run>."""
    words = re.findall(r"[A-Za-z0-9']+", meta.get("title", ""))
    short = words[0] if len(words) == 1 else "".join(w[0].upper() for w in words) or "Draft"
    if len(CFG.get("volumes", [])) > 1 and meta.get("volume"):
        short += f" {meta['volume']}"
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", meta.get("run", ""))
    day = datetime(int(m[1]), int(m[2]), int(m[3])).strftime("%b-%d") if m else ""
    return f"Draftboard: {short} {day}".strip()


def render(analysis: dict, out: Path) -> None:
    template = TEMPLATE.read_text(encoding="utf-8")
    if PLACEHOLDER not in template:
        raise SystemExit(f"Template has no {PLACEHOLDER} placeholder")
    payload = json.dumps(analysis, ensure_ascii=False).replace("</", "<\\/")
    noun = analysis["meta"].get("unit", "chapter")
    words = {"{{HERO}}": analysis["meta"].get("protagonist", "the protagonist"),
             "{{UNIT}}": noun, "{{Unit}}": noun.capitalize(), "{{UNITS}}": noun + "s", "{{Units}}": noun.capitalize() + "s",
             "{{UNIT_SHORT}}": analysis["meta"].get("unit_short", "Ch"),
             "{{WORK}}": "script" if analysis["meta"].get("form") in SCREEN_FORMS else "book",
             "{{PAGE_TITLE}}": html.escape(page_title(analysis["meta"]))}
    for k, v in words.items():
        template = template.replace(k, v)
    out.write_text(template.replace(PLACEHOLDER, payload), encoding="utf-8")


def build(run: Path, analysis: dict) -> int:
    errors, warnings = validate(analysis)
    for w in warnings:
        print(f"warning: {w}")
    for e in errors:
        print(f"ERROR: {e}")
    (run / "analysis.json").write_text(json.dumps(analysis, indent=2, ensure_ascii=False), encoding="utf-8")
    if errors:
        print(f"{len(errors)} errors. Fix them and rerun. explorer.html was not written.")
        return 1
    render(analysis, run / "explorer.html")
    if not analysis["meta"].get("sample"):
        n = write_briefs(run, analysis)
        print(f"{n} {unit_noun()} briefs -> {briefs_dir() / analysis['meta']['book']}")
    findings = sum(len(f.get("findings", [])) for f in analysis["frameworks"])
    states = [x.get("state", {}).get("status") for f in analysis["frameworks"] for x in f.get("findings", [])]
    if any(states):
        closed = sum(s in CLOSED for s in states)
        reopened = [x["id"] for f in analysis["frameworks"] for x in f.get("findings", []) if x.get("state", {}).get("status") == "reopened"]
        print(f"status: {closed} closed, {states.count('partly')} partly fixed"
              + (f", reopened: {', '.join(reopened)}" if reopened else "")
              + (f", {len(analysis.get('confirmed', []))} earlier fixes confirmed" if analysis.get("confirmed") else ""))
    print(f"{len(analysis['frameworks'])} frameworks, {findings} findings, "
          f"{len(analysis.get('convergence', []))} convergence items -> {run / 'explorer.html'}")
    return 0


# ---------- chapter briefs ----------


LEVELS = [(0, 0, "Rest"), (1, 2, "Calm with an undercurrent"), (3, 4, "Low pressure"), (5, 5, "Active threat"),
          (6, 6, "Rising"), (7, 8, "Crisis"), (9, 9, "Converging"), (10, 10, "The climax")]


def level_name(v) -> str:
    return next((name for a, b, name in LEVELS if a <= v <= b), "")


def ch_name(cid: str) -> str:
    label = (CFG.get("labels") or {}).get(cid)
    return label or f"{unit_short()} " + re.sub(r"^0+(?=\d)", "", cid)


def ch_ranges(ids: list, order: dict) -> str:
    ix = sorted({order[i] for i in ids if i in order})
    keys = sorted(order, key=order.get)
    out, start, prev = [], None, None
    for i in ix + [None]:
        if start is None:
            start = prev = i
        elif i is not None and i == prev + 1:
            prev = i
        else:
            a, b = keys[start], keys[prev]
            out.append(ch_name(a) if a == b else f"{ch_name(a)}–{re.sub(r'^0+(?=\d)', '', b)}")
            start = prev = i
    return ", ".join(out)


NOTES_START = "<!-- my-notes:start -->"
NOTES_END = "<!-- my-notes:end -->"


def read_notes(folder: Path) -> dict:
    """Existing hand-written notes in a briefs folder: {chapter id: (title, notes)}."""
    found = {}
    if not folder.is_dir():
        return found
    for f in folder.glob("*.md"):
        if f.name.startswith("_") or f.name == "README.md":
            continue
        text = f.read_text(encoding="utf-8")
        first = text.splitlines()[0] if text else ""
        title = first.split(" · ", 1)[1].strip() if " · " in first else ""
        notes = ""
        if NOTES_START in text and NOTES_END in text:
            notes = text.split(NOTES_START, 1)[1].split(NOTES_END, 1)[0].strip("\n")
        found[f.stem] = (title, notes)
    return found


def notes_block(notes: str) -> list[str]:
    return ["## My notes", "",
            f"Your own issues for this {unit_noun()}. Write between the two markers; everything between them survives rebuilds.", "",
            NOTES_START] + ([notes] if notes.strip() else []) + [NOTES_END, ""]


def status_lines(x: dict) -> list[str]:
    """Brief lines for an open item that has a status: partly fixed, or reopened by a new run."""
    st = x.get("state") or {}
    if st.get("status") == "partly":
        ev = (st.get("evidence") or [{}])[0]
        where = f" ({ch_name(ev['chapter'])} L{ev['line']})" if ev.get("line") else ""
        return ["", f"**Status:** partly fixed {st.get('date', '')}{where}." + (f" {st['note']}" if st.get("note") else "")]
    if st.get("status") == "reopened":
        return ["", f"**Reopened:** marked {st.get('was')} on {st.get('date', '')} (run `{st.get('earlier_run', '')}`), but this run still finds it."
                + (f" Your note then: {st['note']}" if st.get("note") else "")]
    return []


def write_briefs(run: Path, analysis: dict) -> int:
    """One Markdown brief per chapter for Cursor and Claude Code. Generated; never edit by hand."""
    meta, chapters = analysis["meta"], analysis["chapters"]
    order = {c["id"]: i for i, c in enumerate(chapters)}
    total = sum(c["words"] for c in chapters) or 1
    findings = [dict(x, fw=f["key"], fw_name=f["name"]) for f in analysis["frameworks"] for x in f.get("findings", [])]
    by_id = {x["id"]: x for x in findings}
    convs = analysis.get("convergence", [])
    conv_of = {fid: c for c in convs for fid in c.get("findings", [])}
    series = {s["label"]: s for f in analysis["frameworks"] for s in f.get("series", [])}
    tension, peak = series.get("Tension"), series.get("Peak tension")

    LATEST = runs_dir() / "latest.json"
    LATEST.parent.mkdir(parents=True, exist_ok=True)
    latest = load_json(LATEST) if LATEST.exists() else {}
    entry = latest.get(meta["book"], {})
    explorer = entry.get("explorer", "")
    entry.update({"run": run.name, "folder": run.relative_to(PROJECT_ROOT).as_posix(), "git": meta.get("git", ""),
                  "built": datetime.now().strftime("%Y-%m-%d %H:%M"), "explorer": explorer})
    latest[meta["book"]] = entry
    LATEST.write_text(json.dumps(latest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    out_dir = run / "chapters"
    out_dir.mkdir(exist_ok=True)
    stable = briefs_dir() / meta["book"].replace(" ", "-")
    stable.mkdir(parents=True, exist_ok=True)
    entry["briefs"] = stable.relative_to(PROJECT_ROOT).as_posix()
    LATEST.write_text(json.dumps(latest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    old = read_notes(stable)
    new_titles = {c["title"] for c in chapters}
    by_title = {}
    for oid, (t, n) in old.items():
        if n.strip():
            by_title.setdefault(t, []).append(oid)
    used = set()

    def notes_for(cid: str, title: str) -> str:
        # Follow the title first, so notes survive renumbering; fall back to the
        # chapter number only when its old title is gone (a rename).
        for oid in by_title.get(title, []):
            if oid not in used:
                used.add(oid)
                return old[oid][1]
        if cid in old and old[cid][1].strip() and cid not in used and old[cid][0] not in new_titles:
            used.add(cid)
            return old[cid][1]
        return ""

    index, stable_index = [], []
    cum = 0
    for c in chapters:
        cid = c["id"]
        p0 = cum / total
        cum += c["words"]
        p1 = cum / total
        link = f"{explorer}#ch-{cid.replace('.', '-')}" if explorer else ""
        lines = [f"# {ch_name(cid)} · {c['title']}", "",
                 f"<!-- Generated by Draftboard from run {run.name}. Do not edit; rebuild instead. -->", "",
                 f"{meta.get('volume', '')} · {p0:.0%}–{p1:.0%} of the words · {c['words']:,} words · run `{run.name}` at git `{meta.get('git', '')}`", ""]
        if tension and cid in tension.get("values", {}):
            t = tension["values"][cid]
            pk = peak["values"].get(cid) if peak else None
            tline = f"Tension **{t}** ({level_name(t)})"
            if pk is not None and pk != t:
                tline += f", peak **{pk}** ({level_name(pk)})"
            lines.append(tline + ".")
            note = (tension.get("notes") or {}).get(cid)
            if note:
                lines.append(f"- Last page: {note}")
            pnote = (peak.get("notes") or {}).get(cid) if peak else None
            if pnote and pk != t:
                lines.append(f"- Peak: {pnote}")
            lines.append("")
        vshift = series.get("Value shift")
        if vshift and cid in vshift.get("values", {}):
            v = vshift["values"][cid]
            scenes = c.get("scenes") or []
            sign = lambda n: f"+{n}" if n > 0 else (f"−{abs(n)}" if n < 0 else "0")
            size = {1: "a nudge", 2: "a clear turn", 3: "a major reversal"}.get(abs(v), "")
            word = "no change overall" if v == 0 else f"{size} for the {'better' if v > 0 else 'worse'}"
            note = ""
            if v == 0 and any(s.get("shift") for s in scenes):
                note = " The scenes cancel out, so the chapter ends where it started."
            elif v == 0:
                note = " No scene turns a value."
            lines.append(f"Value shift **{sign(v)}** ({word}).{note}")
            for s in scenes:
                lines.append(f"- {sign(s.get('shift') or 0)} {s.get('value', '')}: {s.get('turn', '')}"
                             + (f" (L{s['line']})" if s.get("line") else ""))
            lines.append("")
        lines += [f"This analysis describes `{c['file']}` as of git `{meta.get('git', '')}`. If the chapter changed since, check before acting on them.", ""]

        fix_conv = [cv for cv in convs if cid in cv.get("fix_in", []) and not is_closed(cv)]
        fix_here = [x for x in findings if cid in x.get("fix_in", []) and not is_closed(x)]
        shows = [x for x in findings if cid in x.get("chapters", []) and cid not in x.get("fix_in", []) and not is_closed(x)]
        in_conv = [cv for cv in convs if cid in cv.get("chapters", []) and cv not in fix_conv and not is_closed(cv)]
        closed_here = [cv for cv in convs if cid in cv.get("fix_in", []) and is_closed(cv)] +             [x for x in findings if cid in x.get("fix_in", []) and is_closed(x)]

        lines += [f"## Fix here ({len(fix_conv) + len(fix_here)})", ""]
        if not fix_conv and not fix_here:
            lines += [f"Nothing. No finding names this {unit_noun()} as the place to fix it.", ""]
        for cv in fix_conv:
            fids = [f for f in cv.get("findings", []) if f in by_id]
            lines += [f"### {cv['id']} · {cv['title']}",
                      f"Where frameworks agree ({', '.join(fids)}) · {ch_ranges(cv.get('chapters', []), order)}",
                      "", cv.get("read", ""), "", f"**Fix:** {cv.get('fix', '')}"] + status_lines(cv) + (
                      [f"Progress: {cv['progress']}."] if cv.get("progress") else [])
            others = [i for i in cv.get("fix_in", []) if i != cid]
            if others:
                lines.append(f"Also fix in: {ch_ranges(others, order)}")
            lines.append("")
        for x in sorted(fix_here, key=lambda y: (y["severity"] != "high", y["id"])):
            cv = conv_of.get(x["id"])
            agree = f"part of {cv['id']} {cv['title']}" if cv else "one framework"
            lines += [f"### {x['id']} · {x['severity']} · {x['title']}",
                      f"{x['fw_name']} · shows in {ch_ranges(x['chapters'], order)} · {agree}",
                      "", f"**Problem:** {x.get('problem', '')}", "", f"**Suggestion:** {x.get('suggestion', '')}"] + status_lines(x)
            others = [i for i in x.get("fix_in", []) if i != cid]
            if others:
                lines.append(f"Also fix in: {ch_ranges(others, order)}")
            ev = [e for e in x.get("evidence", []) if e.get("chapter") == cid] or x.get("evidence", [])[:1]
            for e in ev:
                ec = chapters[order[e["chapter"]]] if e.get("chapter") in order else None
                lines += ["", f"> {e.get('quote', '')}  ", f"> {ch_name(e['chapter'])} L{e.get('line')}{' · ' + ec['file'] if ec else ''}"]
            lines.append("")

        if closed_here:
            lines += [f"## Closed here ({len(closed_here)})", "",
                      "Marked closed in Draftboard. Do not raise these again unless the text changes back.", ""]
            for x in closed_here:
                st = x["state"]
                ev = (st.get("evidence") or [{}])[0]
                quote = f" ({ch_name(ev['chapter'])} L{ev['line']}: \"{ev['quote']}\")" if ev.get("quote") else ""
                lines.append(f"- **{x['id']}** {st['status']} {st.get('date', '')} · {x['title']}"
                             + (f". {st['note']}" if st.get("note") else "") + quote)
            lines.append("")

        lines += [f"## Shows here, fix elsewhere ({len(shows)})", ""]
        if not shows:
            lines.append("Nothing.")
        for x in sorted(shows, key=lambda y: (y["severity"] != "high", y["id"])):
            where = ch_ranges(x.get("fix_in", []), order) or "not named"
            cv = conv_of.get(x["id"])
            lines.append(f"- **{x['id']}** {x['severity']} · {x['title']} ({x['fw_name']}{', ' + cv['id'] if cv else ''}) → fix in {where}")
        for cv in in_conv:
            lines.append(f"- Inside **{cv['id']}** {cv['title']} → fix in {ch_ranges(cv.get('fix_in', []), order) or 'not named'}")
        lines.append("")

        opens, closes, running, marks = [], [], [], []
        for f in analysis["frameworks"]:
            for sp in f.get("spans", []):
                a = order.get(sp.get("from"))
                b = len(chapters) - 1 if sp.get("to") is None else order.get(sp.get("to"))
                if a is None or b is None or not (a <= order[cid] <= b):
                    continue
                item = f"{sp.get('label', '')} ({f['name']}{', ' + sp['status'] if sp.get('status', 'ok') != 'ok' else ''})"
                if sp.get("from") == cid:
                    opens.append(item)
                elif sp.get("to") == cid:
                    closes.append(item)
                else:
                    running.append((sp.get("status", "ok") != "ok", item))
            for mk in f.get("marks", []):
                if mk.get("chapter") == cid:
                    st = mk.get("status", "ok")
                    marks.append(f"{mk.get('label', '')} ({f['name']}, {mk.get('row', '')}{', ' + st if st != 'ok' else ''})"
                                 + (f": {mk['note']}" if mk.get("note") else ""))
        lines += ["## Structure here", ""]
        if marks:
            lines += ["Marks on this chapter:"] + [f"- {m}" for m in marks] + [""]
        if opens:
            lines += ["Opens here:"] + [f"- {o}" for o in opens] + [""]
        if closes:
            lines += ["Closes here:"] + [f"- {o}" for o in closes] + [""]
        if running:
            flagged = [i for bad, i in running if bad]
            calm = len(running) - len(flagged)
            lines.append(f"Running through: {len(running)} threads and promises, {len(flagged)} flagged.")
            lines += [f"- {i}" for i in flagged]
            if calm:
                lines.append(f"- and {calm} on track (see the explorer)")
            lines.append("")
        if not (marks or opens or closes or running):
            lines += [f"Nothing mapped on this {unit_noun()}.", ""]
        (out_dir / f"{cid}.md").write_text("\n".join(lines), encoding="utf-8")
        mine = notes_for(cid, c["title"])
        at = lines.index(next(l for l in lines if l.startswith("## Fix here")))
        stable_lines = [l.replace("Do not edit; rebuild instead.", "Only the My notes section is yours to edit; the rest is rebuilt.") for l in lines[:at]] \
            + notes_block(mine) + lines[at:]
        (stable / f"{cid}.md").write_text("\n".join(stable_lines), encoding="utf-8", newline="\n")
        note_count = len([l for l in mine.splitlines() if l.strip()])
        stable_index.append(f"| [{ch_name(cid)}]({cid}.md) | {c['title']} | {note_count or ''} | {len(fix_conv) + len(fix_here)} | {len(shows)} | "
                            f"{tension['values'].get(cid, '') if tension else ''} |")
        index.append(f"| [{ch_name(cid)}]({cid}.md) | {c['title']} | {len(fix_conv) + len(fix_here)} | {len(shows)} | "
                     f"{tension['values'].get(cid, '') if tension else ''} |")
    head = [f"# {unit_noun().capitalize()} briefs · {run.name}", "", "Generated by Draftboard. Do not edit; rebuild instead.", "",
            f"| {unit_noun().capitalize()} | Title | Fix here | Shows here | Tension |", "|---|---|--:|--:|--:|"]
    (out_dir / "README.md").write_text("\n".join(head + index) + "\n", encoding="utf-8")

    unplaced = [(oid, t, n) for oid, (t, n) in old.items() if n.strip() and oid not in used]
    if unplaced:
        dump = stable / "_unplaced-notes.md"
        prev = dump.read_text(encoding="utf-8") if dump.exists() else "# Unplaced notes\n\nNotes the build could not match to a chapter by title or number. Move each one into the right brief's My notes section, then delete it here.\n"
        add = [f"\n## From old {ch_name(oid)} · {t} (build {datetime.now().strftime('%Y-%m-%d %H:%M')})\n\n{n}\n" for oid, t, n in unplaced]
        dump.write_text(prev + "".join(add), encoding="utf-8", newline="\n")
        print(f"WARNING: {len(unplaced)} chapter notes could not be placed; saved to {dump}")
    current = {c["id"] for c in chapters}
    for f in stable.glob("*.md"):
        if not f.name.startswith("_") and f.name != "README.md" and f.stem not in current:
            f.unlink()
    shead = [f"# {unit_noun().capitalize()} briefs · {meta.get('volume', '')}", "",
             f"Current run: `{run.name}`. Rebuilt by Draftboard. Each brief's My notes section is yours and survives rebuilds; the rest is regenerated.", "",
             f"| {unit_noun().capitalize()} | Title | My notes | Fix here | Shows here | Tension |", "|---|---|--:|--:|--:|--:|"]
    (stable / "README.md").write_text("\n".join(shead + stable_index) + "\n", encoding="utf-8", newline="\n")
    return len(chapters)


def cmd_build(args) -> int:
    run = Path(args.run).resolve()
    return build(run, merge(run))


# ---------- sample ----------

def cmd_sample(args) -> int:
    volume = volume_for(args.volume)
    chapters = U.list_units(PROJECT_ROOT, CFG, volume, runs_dir() / "sample")
    hero = CFG["protagonist"]
    ids = [c["id"] for c in chapters]
    n = len(ids)
    rng = random.Random(7)
    total = sum(c["words"] for c in chapters)
    cum, pct = 0, {}
    for c in chapters:
        pct[c["id"]] = (cum + c["words"] / 2) / total
        cum += c["words"]

    def at(p):
        return min(ids, key=lambda i: abs(pct[i] - p))

    def rng_ids(a, b):
        return ids[ids.index(a):ids.index(b) + 1]

    tension = {i: round(max(0, min(10, 2 + 7 * pct[i] ** 1.4 + 1.6 * math.sin(pct[i] * 19) + rng.uniform(-1, 1))), 1)
               for i in ids}
    tension[at(0.97)] = 10
    shift = {i: rng.choice([-3, -2, -1, -1, 0, 0, 1, 1, 2, 3]) for i in ids}
    for i in rng_ids(at(0.62), at(0.68)):
        shift[i] = 0
        tension[i] = round(tension[i] * 0.7, 1)
    open_threads = {i: int(3 + 9 * math.sin(pct[i] * math.pi) + rng.uniform(-1, 1)) for i in ids}
    power = {i: round(1 + 7.5 * pct[i] + (0.8 if pct[i] > 0.5 else 0), 1) for i in ids}

    def beat(label, p, actual=None, status="ok", row="Beats"):
        return {"row": row, "chapter": at(actual if actual is not None else p), "label": label,
                "status": status, "target": f"{round(p * 100)}%", "note": f"Sample note for {label}."}

    sag = rng_ids(at(0.62), at(0.68))
    late = rng_ids(at(0.9), at(0.99))

    def finding(fid, title, sev, chs, problem):
        return {"id": fid, "title": title, "severity": sev, "chapters": chs, "problem": problem,
                "why": ["Sample bullet. A real run explains the framework's evidence here."],
                "evidence": [{"chapter": chs[0], "line": 12, "quote": "Sample quote. A real run quotes the chapter."}],
                "suggestion": "Sample suggestion. A real run gives the structural move."}

    frameworks = [
        {"key": "structure", "name": "Save the Cat", "lens": "Structure", "grade": "mixed",
         "verdict": "Sample verdict. Placeholder data drawn over the real chapter list.",
         "rows": ["Beats", "Spans"],
         "marks": [beat("Opening Image", 0.0), beat("Theme Stated", 0.05, 0.07), beat("Catalyst", 0.10, 0.14, "warn"),
                   beat("Break into Two", 0.20, 0.22), beat("B Story", 0.22, 0.25), beat("Midpoint", 0.5, 0.56, "warn"),
                   beat("All Is Lost", 0.75, 0.86, "problem"), beat("Break into Three", 0.8, 0.9, "problem"),
                   beat("Final Image", 1.0, 0.995)],
         "spans": [{"row": "Spans", "from": ids[0], "to": at(0.1), "label": "Setup", "status": "ok"},
                   {"row": "Spans", "from": at(0.14), "to": at(0.2), "label": "Debate", "status": "ok"},
                   {"row": "Spans", "from": at(0.22), "to": at(0.5), "label": "Fun and Games", "status": "ok"},
                   {"row": "Spans", "from": at(0.56), "to": at(0.84), "label": "Bad Guys Close In", "status": "warn"},
                   {"row": "Spans", "from": at(0.9), "to": ids[-1], "label": "Finale", "status": "ok"}],
         "acts": [{"label": "Act I", "from": ids[0], "to": at(0.2)},
                  {"label": "Act IIa", "from": ids[ids.index(at(0.2)) + 1], "to": at(0.5)},
                  {"label": "Act IIb", "from": ids[ids.index(at(0.5)) + 1], "to": at(0.85)},
                  {"label": "Act III", "from": ids[ids.index(at(0.85)) + 1], "to": ids[-1]}],
         "findings": [finding("ST1", "Sample: All Is Lost lands late", "high", rng_ids(at(0.75), at(0.86)),
                              "Sample problem text."),
                      finding("ST2", "Sample: midpoint is soft", "medium", [at(0.56)], "Sample problem text.")]},
        {"key": "arcs", "name": "Character arcs", "lens": "Weiland", "grade": "strong",
         "verdict": "Sample verdict.", "rows": [hero, "Ally", "Rival"],
         "spans": [{"row": hero, "from": ids[0], "to": ids[-1], "label": "Positive arc: sample Lie", "kind": "positive", "status": "ok"},
                   {"row": "Ally", "from": ids[0], "to": at(0.15), "label": "Flat arc: sample", "kind": "flat", "status": "warn"},
                   {"row": "Rival", "from": at(0.3), "to": None, "label": "Negative arc: sample", "kind": "negative", "status": "ok"}],
         "marks": [{"row": hero, "chapter": at(p), "label": l, "status": s}
                   for p, l, s in [(0.03, "Characteristic moment", "ok"), (0.22, "First plot point", "ok"),
                                   (0.5, "Midpoint truth", "warn"), (0.86, "Third plot point", "ok"), (0.97, "Climax choice", "ok")]]
                  + [{"row": "Rival", "chapter": at(0.6), "label": "Sample beat", "status": "missing"}],
         "findings": [finding("AR1", f"Sample: {hero}'s midpoint truth is thin", "medium", [at(0.5), at(0.56)], "Sample problem text.")]},
        {"key": "promises", "name": "Promises and payoffs", "lens": "Sanderson", "grade": "mixed",
         "verdict": "Sample verdict.", "rows": ["Big promises", "Mysteries", "Clocks", "Power"],
         "spans": [{"row": "Big promises", "from": ids[1], "to": ids[-2], "label": "Sample big promise", "status": "ok"},
                   {"row": "Mysteries", "from": at(0.12), "to": at(0.7), "label": "Sample mystery", "status": "warn"},
                   {"row": "Mysteries", "from": at(0.35), "to": None, "label": "Sample carried hook", "kind": "carried", "status": "ok"},
                   {"row": "Clocks", "from": at(0.4), "to": at(0.93), "label": "Sample clock", "status": "ok"},
                   {"row": "Power", "from": at(0.18), "to": None, "label": "Sample dropped skill", "status": "problem"}],
         "marks": [{"row": "Mysteries", "chapter": at(p), "label": "Progress", "status": "ok"} for p in (0.2, 0.33, 0.45)],
         "findings": [finding("PR1", "Sample: a skill setup is dropped", "high", [at(0.18), at(0.9)], "Sample problem text."),
                      finding("PR2", "Sample: mystery goes silent", "medium", sag, "Sample problem text.")]},
        {"key": "mice", "name": "MICE threads", "lens": "Kowal", "grade": "mixed",
         "verdict": "Sample verdict.", "rows": ["M", "I", "C", "E"],
         "series": [{"label": "Open threads", "type": "line", "min": 0, "values": open_threads}],
         "spans": [{"row": "M", "from": at(0.12), "to": ids[-1], "label": "Sample place", "kind": "M", "status": "ok"},
                   {"row": "I", "from": at(0.05), "to": at(0.8), "label": "Sample question", "kind": "I", "status": "warn"},
                   {"row": "C", "from": ids[0], "to": at(0.98), "label": "Sample inner change", "kind": "C", "status": "ok"},
                   {"row": "E", "from": at(0.1), "to": at(0.9), "label": "Sample event", "kind": "E", "status": "problem"}],
         "marks": [{"row": "E", "chapter": at(0.9), "label": "Closes before inner thread", "status": "problem"}],
         "findings": [finding("MI1", "Sample: outer thread closes first", "high", late, "Sample problem text.")]},
        {"key": "pacing", "name": "Value shifts", "lens": "Story Grid", "grade": "mixed",
         "verdict": "Sample verdict.", "rows": ["Turns", "Sags"],
         "series": [{"label": "Tension", "type": "line", "min": 0, "max": 10, "spine": True, "values": tension},
                    {"label": "Value shift", "type": "bars", "min": -3, "max": 3, "values": shift}],
         "spans": [{"row": "Sags", "from": sag[0], "to": sag[-1], "label": "Sample sag", "status": "problem"}],
         "marks": [{"row": "Turns", "chapter": at(p), "label": l, "status": "ok"}
                   for p, l in [(0.1, "Safe → hunted"), (0.5, "Hope → despair"), (0.86, "Alive → dying"), (0.97, "Trapped → free")]],
         "findings": [finding("PA1", "Sample: sag after the midpoint", "high", sag, "Sample problem text."),
                      finding("PA2", "Sample: finale peaks early", "medium", late[:2], "Sample problem text.")]},
        {"key": "genre", "name": "Genre contract", "lens": "Progression + Action", "grade": "strong",
         "verdict": "Sample verdict.", "rows": ["Rewards", "System", "Obligatory", "Tone"],
         "series": [{"label": f"{hero}'s power", "type": "line", "min": 0, "max": 10, "values": power}],
         "spans": [{"row": "Rewards", "from": sag[0], "to": sag[-1], "label": "Sample drought", "status": "warn"}],
         "marks": [{"row": "Rewards", "chapter": at(p), "label": "Reward", "status": "ok"} for p in (0.2, 0.3, 0.42, 0.55, 0.75, 0.95)]
                  + [{"row": "Obligatory", "chapter": at(0.9), "label": "Hero at the mercy of the villain", "status": "missing"},
                     {"row": "Tone", "chapter": at(0.3), "label": "Comedy beat", "kind": "comedy", "status": "ok"}],
         "findings": [finding("GE1", "Sample: reward drought", "medium", sag, "Sample problem text.")]},
    ]
    composer = {
        "sample": True,
        "headline": f"Sample data. These findings are placeholders drawn over the real {unit_noun()} list so you can try the explorer.",
        "convergence": [
            {"id": "C1", "title": "Sample: the post-midpoint stretch stalls", "chapters": sag,
             "findings": ["PA1", "PR2", "GE1"], "read": "Sample read. A real run says what each framework saw and the cause.",
             "fix": "Sample fix."},
            {"id": "C2", "title": "Sample: the ending closes threads out of order", "chapters": late,
             "findings": ["MI1", "ST1", "PA2"], "read": "Sample read.", "fix": "Sample fix."},
        ],
    }
    run = runs_dir() / "sample"
    (run / "frameworks").mkdir(parents=True, exist_ok=True)
    (run / "chapters.json").write_text(json.dumps({"book": volume["key"], "volume": volume["label"], "git": "sample", "created": "sample",
                                                    "chapters": chapters}, indent=2, ensure_ascii=False), encoding="utf-8")
    for fw in frameworks:
        (run / "frameworks" / f"{fw['key']}.json").write_text(json.dumps(fw, indent=2, ensure_ascii=False), encoding="utf-8")
    (run / "composer.json").write_text(json.dumps(composer, indent=2, ensure_ascii=False), encoding="utf-8")
    return build(run, merge(run))


def main() -> int:
    global PROJECT_ROOT, CFG
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project", help="Project folder (default: the nearest folder with a draftboard.json)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("check")
    p = sub.add_parser("units")
    p.add_argument("--volume")
    p.add_argument("--run")
    p.add_argument("--groups", type=int, default=0)
    p = sub.add_parser("ledger")
    p.add_argument("run")
    p = sub.add_parser("build")
    p.add_argument("run")
    p = sub.add_parser("sample")
    p.add_argument("--volume")
    p = sub.add_parser("status", help="Mark a finding or convergence item fixed, partly, kept or stale (or open again)")
    p.add_argument("id", nargs="?", help="Finding or convergence id, for example AR3 or C2")
    p.add_argument("state", nargs="?", choices=STATES + ("open",))
    p.add_argument("--note")
    p.add_argument("--evidence", action="append", help="CHAPTER:LINE:QUOTE from the current text; repeatable")
    p.add_argument("--volume")
    p.add_argument("--list", action="store_true")
    p = sub.add_parser("link", help="Record the published explorer URL for a volume, so briefs link to it")
    p.add_argument("url")
    p.add_argument("--volume")
    args = parser.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    PROJECT_ROOT = find_project(Path(args.project).resolve() if args.project else Path.cwd())
    CFG = load_config(PROJECT_ROOT)
    return {"check": cmd_check, "units": cmd_units, "ledger": cmd_ledger, "build": cmd_build,
            "sample": cmd_sample, "link": cmd_link, "status": cmd_status}[args.cmd](args)


# ---------- issue status ----------

STATES = ("fixed", "partly", "kept", "stale")
CLOSED = ("fixed", "kept", "stale")


def status_path(volume_key: str) -> Path:
    return briefs_dir() / volume_key.replace(" ", "-") / "_status.json"


def load_status(volume_key: str) -> list[dict]:
    p = status_path(volume_key)
    return load_json(p).get("items", []) if p.exists() else []


def save_status(volume_key: str, items: list[dict]) -> None:
    p = status_path(volume_key)
    p.parent.mkdir(parents=True, exist_ok=True)
    doc = {"about": "Draftboard issue status. Written by `draftboard.py status`; survives rebuilds and new runs.",
           "items": items}
    p.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def apply_status(analysis: dict) -> None:
    """Attach each finding's and convergence item's status from the volume's status file."""
    meta = analysis["meta"]
    items = load_status(meta["book"])
    run = meta["run"]
    if not items:
        return
    latest = lambda xs: max(xs, key=lambda e: e.get("date", "")) if xs else None
    matched = set()

    def find(kind: str, xid: str, title: str, fw: str = ""):
        same = [e for e in items if e.get("kind") == kind and e.get("run") == run and e.get("id") == xid]
        if same:
            return same[-1]
        older = [e for e in items if e.get("kind") == kind and e.get("run") != run and e.get("title") == title
                 and e.get("framework", "") == fw]
        return latest(older)

    def state_for(e: dict) -> dict:
        s = {k: e.get(k) for k in ("status", "date", "note", "evidence", "git") if e.get(k)}
        if e.get("run") != run:
            s["earlier_run"] = e.get("run")
            if e["status"] in ("fixed", "stale"):
                s = {"status": "reopened", "was": e["status"], "date": e.get("date"), "note": e.get("note", ""),
                     "earlier_run": e.get("run")}
        return s

    for fw in analysis["frameworks"]:
        for x in fw.get("findings", []):
            e = find("finding", x["id"], x["title"], fw.get("key", ""))
            if e:
                matched.add(id(e))
                x["state"] = state_for(e)
    by_id = {x["id"]: x for fw in analysis["frameworks"] for x in fw.get("findings", [])}
    for c in analysis.get("convergence", []):
        e = find("convergence", c["id"], c["title"])
        if e:
            matched.add(id(e))
            c["state"] = state_for(e)
            continue
        fs = [by_id[f] for f in c.get("findings", []) if f in by_id]
        closed = [x for x in fs if x.get("state", {}).get("status") in CLOSED]
        if fs and len(closed) == len(fs):
            c["state"] = {"status": "fixed", "derived": True, "date": max(x["state"].get("date", "") for x in closed),
                          "note": "All of its findings are closed."}
        elif closed:
            c["progress"] = f"{len(closed)} of {len(fs)} findings closed"
    analysis["confirmed"] = [{k: e.get(k) for k in ("id", "title", "framework", "date", "note", "run")}
                             for e in items if e.get("run") != run and e.get("status") == "fixed" and id(e) not in matched]


def is_closed(x: dict) -> bool:
    return x.get("state", {}).get("status") in CLOSED


def norm_quote(s: str) -> str:
    s = s.replace("’", "'").replace("‘", "'").replace("“", '"').replace("”", '"').replace("—", "-")
    return re.sub(r"[\s*_]+", " ", s).strip().lower()


def check_evidence(ev: str, chapters: dict) -> dict:
    """CH:LINE:QUOTE -> the quote found in that unit's text, with its real line number."""
    m = re.match(r"^([^:]+):(\d+):(.+)$", ev, re.S)
    if not m:
        raise SystemExit(f"Evidence must be CHAPTER:LINE:QUOTE, got {ev!r}")
    cid, line, quote = m[1].strip(), int(m[2]), m[3].strip().strip('"')
    c = chapters.get(cid)
    if not c:
        raise SystemExit(f"Unknown {unit_noun()} {cid!r} in evidence")
    lines = (PROJECT_ROOT / c["file"]).read_text(encoding="utf-8").splitlines()
    lo, hi = (c.get("start", 1), c.get("end", len(lines))) if c.get("start") else (1, len(lines))
    want = norm_quote(quote)
    order = sorted(range(lo, hi + 1), key=lambda n: (abs(n - line), n))
    for n in order:
        if 1 <= n <= len(lines) and want in norm_quote(lines[n - 1]):
            return {"chapter": cid, "line": n, "quote": quote}
    raise SystemExit(f"Quote not found in {c['file']} ({ch_name(cid)}): {quote!r}. Nothing was marked.")


def cmd_status(args) -> int:
    volume = volume_for(args.volume)
    latest = load_json(runs_dir() / "latest.json") if (runs_dir() / "latest.json").exists() else {}
    entry = latest.get(volume["key"])
    if not entry:
        raise SystemExit(f"No run for {volume['label']} yet. Run /draftboard:map first.")
    run = PROJECT_ROOT / entry["folder"]
    analysis = merge(run)
    items = load_status(volume["key"])

    if args.list or not args.id:
        if not items:
            print(f"{volume['label']}: no findings marked yet.")
        for e in sorted(items, key=lambda e: e.get("date", "")):
            here = "" if e.get("run") == run.name else f" (from run {e.get('run')})"
            print(f"{e['id']:>5}  {e['status']:<7} {e.get('date', '')}  {e.get('title', '')}{here}"
                  + (f"  · {e['note']}" if e.get("note") else ""))
        return 0

    findings = {x["id"]: (x, fw) for fw in analysis["frameworks"] for x in fw.get("findings", [])}
    convs = {c["id"]: c for c in analysis.get("convergence", [])}
    xid = args.id.upper()
    if xid in findings:
        x, fw = findings[xid]
        base = {"id": xid, "kind": "finding", "framework": fw.get("key", ""), "title": x["title"],
                "chapters": x.get("chapters", []), "fix_in": x.get("fix_in", [])}
    elif xid in convs:
        c = convs[xid]
        base = {"id": xid, "kind": "convergence", "title": c["title"],
                "chapters": c.get("chapters", []), "fix_in": c.get("fix_in", [])}
    else:
        raise SystemExit(f"No finding or convergence item {xid!r} in run {run.name}.")

    same = lambda e: e.get("run") == run.name and e.get("id") == xid
    if args.state == "open":
        kept = [e for e in items if not same(e)]
        if len(kept) == len(items):
            print(f"{xid} was not marked.")
            return 0
        save_status(volume["key"], kept)
        print(f"{xid} reopened.")
        return build(run, merge(run))

    if args.state in ("fixed", "partly") and not args.evidence:
        raise SystemExit(f"Marking {xid} {args.state} needs --evidence CHAPTER:LINE:QUOTE from the current text.")
    if args.state in ("kept", "stale") and not args.note:
        raise SystemExit(f"Marking {xid} {args.state} needs --note saying why.")
    chapters = {c["id"]: c for c in analysis["chapters"]}
    evidence = [check_evidence(ev, chapters) for ev in (args.evidence or [])]
    sha = git("rev-parse", "--short", "HEAD")
    dirty = bool(git("status", "--porcelain"))
    new = dict(base, status=args.state, date=datetime.now().strftime("%Y-%m-%d"),
               git=sha + (" (uncommitted changes)" if dirty and sha else ""), run=run.name,
               note=args.note or "", evidence=evidence)
    items = [e for e in items if not same(e)] + [new]
    save_status(volume["key"], items)
    print(f"{xid} marked {args.state}: {base['title']}")
    for ev in evidence:
        print(f"  {ch_name(ev['chapter'])} L{ev['line']}: {ev['quote']}")
    return build(run, merge(run))


def cmd_link(args) -> int:
    volume = volume_for(args.volume)
    latest_path = runs_dir() / "latest.json"
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    latest = load_json(latest_path) if latest_path.exists() else {}
    latest.setdefault(volume["key"], {})["explorer"] = args.url
    latest_path.write_text(json.dumps(latest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{volume['label']}: explorer link saved. Rebuild to put it in the briefs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
