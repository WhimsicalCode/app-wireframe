# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow>=11,<13"]
# ///
"""Place screenshots dropped on a wireframe board next to their wireframes.

Offline, like wireframes.py: the agent reads the board and says which dropped image is
which screen; this script checks that mapping and computes the moves.

  uv run scripts/arrange.py contact <run>
  uv run scripts/arrange.py plan <run> <listing> <mapping.json>
  uv run scripts/arrange.py verify <run> <listing>

Frames are first placed on the board grid (1439 px between columns, 1376 px between rows,
anchored on screen 01's frame) so each wireframe and screenshot pair stands apart. Each
screenshot becomes 852 px tall (width from its aspect ratio), 132 px right of its frame and
4 px below the frame's top; its credit link moves 20 px below it, left-aligned. Screens
without a screenshot keep their link under the frame.
"""

import argparse
import json
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from wireframes import (  # noqa: E402
    COLUMN_PITCH,
    COLUMNS,
    FRAME_H,
    FRAME_W,
    LINK_GAP,
    LINK_TEXT,
    ROW_PITCH,
    SHOT_GAP,
    SHOT_H,
    SHOT_TOP,
    listing_rows,
    load,
    now,
)

TOLERANCE = 2


def arrange_dir(run):
    path = Path(run) / "arrange"
    path.mkdir(exist_ok=True)
    return path


def rect(row):
    return tuple(float(row[k]) for k in ("x", "y", "width", "height"))


def overlaps(a, b):
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def close(a, b):
    return all(abs(x - y) <= TOLERANCE for x, y in zip(a, b))


def board_listing(path):
    raw = Path(path).read_text()
    if re.search(r"Showing \d+ of \d+", raw):
        sys.exit("The listing is truncated: fetch with limit 200 (and select_kinds frame, attachment, image, link).")
    rows = listing_rows(raw)
    if rows and "x" not in rows[0]:
        sys.exit("The listing has no positions: fetch with detail 'detailed'.")
    return rows


def link_url(row):
    match = re.search(r"\[url: (\S+?)\]", row.get("raw_text", ""))
    return match.group(1) if match else None


def cmd_contact(args):
    """One labelled sheet of the run's screenshots, to compare against snapshots of the dropped images."""
    state = load(args.run)
    thumb_w, cols, label_h = 200, 5, 28
    thumbs = []
    for screen in state["screens"]:
        with Image.open(Path(state["source"]) / screen["file"]) as image:
            image = image.convert("RGB")
            thumbs.append((screen, image.resize((thumb_w, round(image.height * thumb_w / image.width)))))
    thumb_h = max(t.height for _, t in thumbs)
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * (thumb_w + 16) + 16, rows * (thumb_h + label_h + 16) + 16), "white")
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.load_default(size=15)
    except TypeError:
        font = ImageFont.load_default()
    for i, (screen, thumb) in enumerate(thumbs):
        x = 16 + (i % cols) * (thumb_w + 16)
        y = 16 + (i // cols) * (thumb_h + label_h + 16)
        draw.text((x, y), f"{screen['key']} {screen['label']}"[:24], fill=(0, 0, 0), font=font)
        sheet.paste(thumb, (x, y + label_h))
    out = arrange_dir(args.run) / "contact.png"
    sheet.save(out)
    print(json.dumps({"contact_sheet": str(out), "screens": len(thumbs)}))


def frame_targets(state, frames, keep):
    """Top-left of every frame on the board grid, anchored on the first screen's frame."""
    placed = [s for s in state["screens"] if s.get("frame_id") in frames]
    if not placed:
        sys.exit("None of the run's frames are on this board.")
    if keep:
        return {s["key"]: rect(frames[s["frame_id"]])[:2] for s in placed}
    ox, oy = rect(frames[placed[0]["frame_id"]])[:2]
    index = {s["key"]: i for i, s in enumerate(state["screens"])}
    first = index[placed[0]["key"]]
    out = {}
    for screen in placed:
        i = index[screen["key"]] - first
        out[screen["key"]] = (ox + (i % COLUMNS) * COLUMN_PITCH, oy + (i // COLUMNS) * ROW_PITCH)
    return out


def cmd_plan(args):
    state = load(args.run)
    rows = board_listing(args.listing)
    by_id = {r["id"]: r for r in rows}
    frames = {r["id"]: r for r in rows if r["kind"] == "frame"}
    attachments = {r["id"]: r for r in rows if r["kind"] in ("attachment", "image")}
    links = [r for r in rows if r["kind"] == "link"]
    mapping = json.loads(Path(args.mapping).read_text())
    screens = {s["key"]: s for s in state["screens"]}

    problems = []
    unknown = [a for a in mapping if a not in attachments]
    if unknown:
        problems.append(f"not images on this board: {', '.join(unknown)}")
    keys = list(mapping.values())
    duplicates = sorted({k for k in keys if keys.count(k) > 1})
    if duplicates:
        problems.append(f"screens matched more than once: {', '.join(duplicates)}")
    missing_keys = [k for k in keys if k not in screens]
    if missing_keys:
        problems.append(f"no such screen keys in the run: {', '.join(missing_keys)}")
    unmapped = [a for a in attachments if a not in mapping]
    if unmapped and not args.allow_unmapped:
        problems.append(f"images on the board not in the mapping: {', '.join(unmapped)} "
                        "(identify them, or pass --allow-unmapped to leave them where they are)")
    for key in keys:
        screen = screens.get(key)
        if screen and screen.get("frame_id") not in frames:
            problems.append(f"screen {key}'s frame {screen.get('frame_id')} isn't on the board")
    if problems:
        sys.exit("Not arranging:\n  " + "\n  ".join(problems))

    by_key = {key: attachment_id for attachment_id, key in mapping.items()}
    run_frames = {s["frame_id"] for s in state["screens"]}
    others = [f for fid, f in frames.items() if fid not in run_frames]
    positions = frame_targets(state, frames, args.keep_frames)
    operations, plan, notes, claimed = [], [], [], []
    for key, (fx, fy) in positions.items():
        screen = screens[key]
        frame_id = screen["frame_id"]
        if not close(rect(frames[frame_id])[:2], (fx, fy)):
            operations.append({"op": "update", "id": frame_id, "x": fx, "y": fy})
        item = {"key": key, "frame_id": frame_id, "frame": {"x": fx, "y": fy}, "attachment_id": by_key.get(key)}
        boxes = [(fx, fy, FRAME_W, FRAME_H)]
        if key in by_key:
            width = round(SHOT_H * screen["width"] / screen["height"])
            shot = {"x": fx + FRAME_W + SHOT_GAP, "y": fy + SHOT_TOP, "width": width, "height": SHOT_H}
            boxes.append((shot["x"], shot["y"], width, SHOT_H))
            if not close(rect(attachments[by_key[key]]), boxes[-1]):
                operations.append({"op": "update", "id": by_key[key], **shot})
            item["screenshot"] = shot
            link_target = {"x": shot["x"], "y": shot["y"] + SHOT_H + LINK_GAP}
        else:
            link_target = {"x": fx, "y": fy + FRAME_H + LINK_GAP}
        for box in boxes:
            clash = [k for k, other in claimed if overlaps(box, other)]
            clash += [f["text"] for f in others if overlaps(box, rect(f))]
            if clash:
                sys.exit(f"Screen {key} would overlap {', '.join(map(str, clash))}. Move the other content away "
                         "from the frames first.")
        claimed += [(key, box) for box in boxes]

        link_id = screen.get("link_id")
        url = screen.get("mobbin_url")
        if link_id not in by_id:
            same_url = [r["id"] for r in links if url and link_url(r) == url]
            link_id = same_url[0] if len(same_url) == 1 else None
        if link_id:
            if not close(rect(by_id[link_id])[:2], (link_target["x"], link_target["y"])):
                operations.append({"op": "update", "id": link_id, **link_target})
        elif url:
            operations.append({"op": "add", "type": "link", "url": url, "text": LINK_TEXT,
                               "temp_id": f"link{key}", **link_target})
            notes.append(f"screen {key} had no credit link on the board; adding one "
                         "(record it with `wireframes.py set <run> <key> link_id=<id>`)")
        item.update(link_id=link_id, link=link_target)
        plan.append(item)

    without = sorted(k for k in positions if k not in by_key)
    if without:
        notes.append(f"no screenshot for screens {', '.join(without)}; their links stay under the frame")
    out = arrange_dir(args.run)
    edit = {"id": state["board_id"], "operations": operations}
    (out / "edit.json").write_text(json.dumps(edit, separators=(",", ":")) + "\n")
    (out / "plan.json").write_text(json.dumps({"board_id": state["board_id"], "planned": now(), "status": "planned",
                                               "items": plan}, indent=1) + "\n")
    for note in notes:
        print(f"note: {note}", file=sys.stderr)
    moved = sum(1 for o in operations if o.get("id") in frames)
    print(json.dumps({"operations": len(operations), "frames_moved": moved, "screenshots": len(by_key)}))
    print(json.dumps(edit, separators=(",", ":")))


def cmd_verify(args):
    path = arrange_dir(args.run) / "plan.json"
    if not path.exists():
        sys.exit("Run `plan` first.")
    plan = json.loads(path.read_text())
    rows = {r["id"]: r for r in board_listing(args.listing)}
    problems = []
    for item in plan["items"]:
        checks = [("frame", item["frame_id"], item["frame"]), ("link", item.get("link_id"), item["link"])]
        if item.get("attachment_id"):
            checks.append(("screenshot", item["attachment_id"], item["screenshot"]))
        for name, object_id, want in checks:
            if not object_id:
                continue
            row = rows.get(object_id)
            if not row:
                problems.append(f"{item['key']}: {name} {object_id} is gone")
                continue
            got = dict(zip(("x", "y", "width", "height"), rect(row)))
            if any(abs(got[k] - v) > TOLERANCE for k, v in want.items()):
                problems.append(f"{item['key']}: {name} at {got}, expected {want}")
    if problems:
        sys.exit("Not where planned (if the edit just ran, wait ~15 s and fetch again):\n  " + "\n  ".join(problems))
    plan.update(status="complete", verified=now())
    path.write_text(json.dumps(plan, indent=1) + "\n")
    print(json.dumps({"verified": len(plan["items"])}))


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("contact", help="labelled contact sheet of the run's screenshots")
    p.add_argument("run")
    p.set_defaults(func=cmd_contact)
    p = sub.add_parser("plan", help="check the mapping and print the edit that places screenshots and links")
    p.add_argument("run")
    p.add_argument("listing", help="saved fetch of frames, images and links (detailed, limit 200)")
    p.add_argument("mapping", help='JSON object {"<image id>": "<screen key>"}')
    p.add_argument("--allow-unmapped", action="store_true")
    p.add_argument("--keep-frames", action="store_true", help="leave frames where they are")
    p.set_defaults(func=cmd_plan)
    p = sub.add_parser("verify", help="check a fresh listing against the plan")
    p.add_argument("run")
    p.add_argument("listing")
    p.set_defaults(func=cmd_verify)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
