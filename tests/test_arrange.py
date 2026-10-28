import json
from pathlib import Path

import pytest
from conftest import run_script

HEADER = "type,id,parentId,x,y,width,height,color,text"
BOARD = [
    ("frame", "F1", "", 0, 8, 432, 892, "White", "01 Screen 0"),
    ("frame", "F2", "", 1439, 8, 432, 892, "White", "02 Screen 1"),
    ("link", "L1", "", 0, 920, 24, 24, "Slate", "See screen on Mobbin.com [url: https://mobbin.com/screens/00000000]"),
    ("link", "L2", "", 1439, 920, 24, 24, "Slate", "See screen on Mobbin.com [url: https://mobbin.com/screens/00000001]"),
    ("attachment", "A", "", 3000, 3000, 1179, 2556, "Slate", ""),
    ("attachment", "B", "", 4000, 3000, 1290, 2796, "Slate", ""),
]


def cli(*args, check=True):
    return run_script("arrange.py", *args, check=check)


@pytest.fixture
def run(make_run):
    path = make_run()
    run_script("wireframes.py", "board", path, "--id", "BOARD")
    run_script("wireframes.py", "set", path, "01", "frame_id=F1", "link_id=L1")
    run_script("wireframes.py", "set", path, "02", "frame_id=F2", "link_id=L2")
    return path


def listing(tmp_path, rows, name="board.json"):
    lines = [HEADER] + [",".join(map(str, r)) for r in rows]
    path = tmp_path / name
    path.write_text(json.dumps({"id": "BOARD", "text": "Board: n objects.\n\n" + "\n".join(lines)}))
    return path


def mapping(tmp_path, value):
    path = tmp_path / "mapping.json"
    path.write_text(json.dumps(value))
    return path


def plan(run, board, mapping_path, *extra, check=True):
    result = cli("plan", run, board, mapping_path, *extra, check=check)
    if result.returncode:
        return result, None
    summary, edit = result.stdout.splitlines()
    return json.loads(summary), json.loads(edit)


def test_places_screenshots_and_links_beside_their_frames(run, tmp_path):
    summary, edit = plan(run, listing(tmp_path, BOARD), mapping(tmp_path, {"B": "02", "A": "01"}))
    assert summary == {"operations": 4, "frames_moved": 0, "screenshots": 2}
    assert edit["operations"] == [
        {"op": "update", "id": "A", "x": 564.0, "y": 12.0, "width": 393, "height": 852},
        {"op": "update", "id": "L1", "x": 564.0, "y": 884.0},
        {"op": "update", "id": "B", "x": 2003.0, "y": 12.0, "width": 393, "height": 852},
        {"op": "update", "id": "L2", "x": 2003.0, "y": 884.0},
    ]
    assert json.loads((run / "arrange" / "edit.json").read_text()) == edit


@pytest.mark.parametrize("value, fragment", [
    ({"A": "01", "B": "01"}, "more than once"),
    ({"A": "01", "X": "02"}, "not images on this board"),
    ({"A": "01"}, "not in the mapping"),
    ({"A": "01", "B": "09"}, "no such screen"),
])
def test_refuses_bad_mappings(run, tmp_path, value, fragment):
    result, _ = plan(run, listing(tmp_path, BOARD), mapping(tmp_path, value), check=False)
    assert result.returncode != 0 and fragment in result.stderr


def test_unmapped_images_can_be_left_alone(run, tmp_path):
    summary, _ = plan(run, listing(tmp_path, BOARD), mapping(tmp_path, {"A": "01"}), "--allow-unmapped")
    assert summary["screenshots"] == 1


def test_respaces_crowded_frames_onto_the_board_grid(run, tmp_path):
    crowded = [r if r[1] != "F2" else ("frame", "F2", "", 700, 8, 432, 892, "White", "02 Screen 1") for r in BOARD]
    board, mapped = listing(tmp_path, crowded), mapping(tmp_path, {"A": "01", "B": "02"})
    summary, edit = plan(run, board, mapped)
    assert summary["frames_moved"] == 1
    assert {"op": "update", "id": "F2", "x": 1439.0, "y": 8.0} in edit["operations"]
    assert {"op": "update", "id": "B", "x": 2003.0, "y": 12.0, "width": 393, "height": 852} in edit["operations"]
    kept, _ = plan(run, board, mapped, "--keep-frames", check=False)
    assert kept.returncode != 0 and "overlap" in kept.stderr


def test_refuses_to_overlap_unrelated_content(run, tmp_path):
    board = BOARD + [("frame", "OTHER", "", 600, 100, 300, 300, "White", "Someone else's frame")]
    result, _ = plan(run, listing(tmp_path, board), mapping(tmp_path, {"A": "01", "B": "02"}), check=False)
    assert result.returncode != 0 and "Someone else's frame" in result.stderr


def test_finds_a_link_by_url_or_adds_a_missing_one(run, tmp_path):
    run_script("wireframes.py", "set", run, "01", "link_id=GONE")
    board = [r for r in BOARD if r[1] != "L2"]
    result = cli("plan", run, listing(tmp_path, board), mapping(tmp_path, {"A": "01", "B": "02"}))
    ops = json.loads(result.stdout.splitlines()[1])["operations"]
    assert {"op": "update", "id": "L1", "x": 564.0, "y": 884.0} in ops
    assert any(o["op"] == "add" and o["url"].endswith("00000001") for o in ops)
    assert "adding one" in result.stderr


def test_verify_checks_a_fresh_listing(run, tmp_path):
    plan(run, listing(tmp_path, BOARD), mapping(tmp_path, {"A": "01", "B": "02"}))
    assert cli("verify", run, listing(tmp_path, BOARD, "stale.json"), check=False).returncode != 0
    moved = [("frame", "F1", "", 0, 8, 432, 892, "White", "01"), ("frame", "F2", "", 1439, 8, 432, 892, "White", "02"),
             ("attachment", "A", "", 564, 12, 393, 852, "Slate", ""),
             ("attachment", "B", "", 2003, 12, 393, 852, "Slate", ""),
             ("link", "L1", "", 564, 884, 24, 24, "Slate", "x"), ("link", "L2", "", 2003, 884, 24, 24, "Slate", "x")]
    assert json.loads(cli("verify", run, listing(tmp_path, moved, "fresh.json")).stdout) == {"verified": 2}
    assert json.loads((run / "arrange" / "plan.json").read_text())["status"] == "complete"


def test_contact_sheet(run):
    out = json.loads(cli("contact", run).stdout)
    assert Path(out["contact_sheet"]).exists() and out["screens"] == 2
