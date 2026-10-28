import json
from pathlib import Path

import pytest
import wireframes as wf
from conftest import run_script
from PIL import Image


def cli(*args, check=True):
    return run_script("wireframes.py", *args, check=check)


def text(t, size="m", **style):
    return ["text", {"text": t, "font-size": size, "text-align": "left",
                     "layout/style": {"height": wf.LINE_H[size], **style}}]


def col(*children, **attrs):
    return ["div", {"layout/style": {"flex-direction": "column"}, **attrs}, *children]


def row(*children, **attrs):
    return ["div", {"layout/style": {"flex-direction": "row"}, **attrs}, *children]


def errors(layout):
    return wf.lint_layout(layout).errors


def listing(frame, rows):
    """Detailed fetch listing; rows are (kind, id, text) or (kind, id, text, (x, y, w, h))."""
    lines = []
    for item in rows:
        kind, ident, label = item[:3]
        x, y, w, h = item[3] if len(item) > 3 else (0, 0, 10, 10)
        props = ' [props: {"text_align":"left"}]' if label else ""
        lines.append(f"{kind},{ident},{frame},{x},{y},{w},{h},Slate,{label}{props}")
    header = "type,id,parentId,x,y,width,height,color,text"
    return json.dumps({"id": "board", "text": f"Board: {len(rows)} objects.\n\n{header}\n" + "\n".join(lines)})


# ---------------------------------------------------------------- draft checks

def test_valid_card_layout_passes():
    card = col(
        ["w-shape", {"color": "light-gray", "deco": "fill", "layout/style": {"height": 80, "margin": {"bottom": -80}}}],
        col(text("**Title**"), row(text("Meta", "s", flex=1),
                                   ["icon", {"icon-name": "favorite", "deco": "outline", "wf/color": "red",
                                             "layout/style": {"width": 20, "height": 20}}])),
        **{"wf/group": "card"},
    )
    lint = wf.lint_layout(col(card))
    assert lint.errors == []
    assert lint.groups == {"card": [0, 1, 2, 3]}
    assert [leaf["tag"] for leaf in lint.leaves] == ["w-shape", "text", "text", "icon"]
    assert lint.leaves[3]["color"] == "red"


@pytest.mark.parametrize("layout, fragment", [
    (col(["text", {"text": "x", "text-align": "left"}]), "needs layout/style height"),
    (col(["text", {"text": "x", "layout/style": {"height": 24}}]), "needs text-align"),
    (col(row(["text", {"text": "x", "text-align": "left", "layout/style": {"height": 24}}])), "needs a width or flex"),
    (["div", {"layout/style": {"margin": {"top": 4}, "flex-direction": "column"}}], "Containers can't take margin"),
    (["div", {}], "flex-direction explicitly"),
    (col(["w-shape", {}, text("x")]), "can't have children"),
    (col(["w-image", {}]), "unknown tag"),
    (col(["icon", {"icon-name": "favorite", "deco": "outline", "color": "red",
                   "layout/style": {"width": 20, "height": 20}}]), "doesn't take 'color'"),
    (col(["icon", {"icon-name": "favorite", "layout/style": {"width": 20, "height": 20}}]), "deco: outline"),
    (col(["icon", {"icon-name": "favorite", "deco": "outline"}]), "width and height"),
    (col(["w-icon", {"icon-name": "plus"}]), "draws something else"),
    (col(["w-icon", {"icon-name": "notification"}]), "isn't in the icon set"),
    (col(["w-h-tabs", {"items": [{"text": "Home"}]}]), "plain strings"),
    (col(["w-toggle", {}]), "w-toggle state"),
    (col(text("**Almost gone.** This")), "closing **"),
    (col(["w-button", {"text": "Go", "size": "m", "font-size": "s"}]), "not both"),
    (col(["w-shape", {"color": "teal"}]), "isn't a palette color"),
    (col(["w-stars", {"pos": 4.5}]), "pos must be between 0 and 1"),
    (col(col(text("a"), **{"wf/group": "outer"}), col(col(text("b"), **{"wf/group": "x"}), **{"wf/group": "y"})),
     "only one level"),
])
def test_check_catches_layouts_that_render_badly(layout, fragment):
    assert any(fragment in message for message in errors(layout)), errors(layout)


def test_nbsp_after_marker_is_fine():
    assert errors(col(text("**Almost gone.**\u00a0This"))) == []


def test_warns_on_heavy_placeholders_and_outlined_cards():
    lint = wf.lint_layout(col(
        ["w-shape", {"color": "silver", "icon-name": "image", "layout/style": {"height": 100}}],
        ["w-shape", {"color": "white", "deco": "outline", "layout/style": {"width": 360, "height": 120}}]))
    assert any("looks heavy" in w for w in lint.warnings)
    assert any("outlined card" in w for w in lint.warnings)


def test_clean_strips_draft_annotations_only():
    layout = col(["icon", {"icon-name": "x", "deco": "outline", "wf/color": "red"}], **{"wf/group": "g"})
    assert wf.clean(layout) == ["div", {"layout/style": {"flex-direction": "column"}},
                                ["icon", {"icon-name": "x", "deco": "outline"}]]


def test_strip_markdown_matches_rendered_text():
    assert wf.strip_markdown("~~£2.49~~\u00a0£0 fee") == "£2.49 £0 fee"
    assert wf.strip_markdown("**Almost gone.**\u00a0This") == "Almost gone. This"


def test_check_command_exit_code(tmp_path):
    good, bad = tmp_path / "good.json", tmp_path / "bad.json"
    good.write_text(json.dumps(col(text("Hello"))))
    bad.write_text(json.dumps(col(["w-image", {}])))
    assert cli("check", good).returncode == 0
    assert cli("check", bad, check=False).returncode == 1


# ---------------------------------------------------------------- ledger

def test_init_reads_selection_and_refuses_reinit(make_run):
    run = make_run()
    state = json.loads((run / "run.json").read_text())
    assert state["app"] == "Demo"
    assert [s["title"] for s in state["screens"]] == ["01 Screen 0", "02 Screen 1"]
    assert state["screens"][1]["mobbin_url"].endswith("00000001")
    assert cli("init", run, check=False).returncode != 0


def test_init_accepts_a_plain_screenshot_folder(tmp_path):
    shots = tmp_path / "shots"
    shots.mkdir()
    Image.new("RGB", (1179, 2556), "white").save(shots / "checkout.png")
    cli("init", tmp_path / "Checkout", "--screenshots", shots, "--app", "My app")
    state = json.loads((tmp_path / "Checkout" / "run.json").read_text())
    assert state["app"] == "My app"
    assert state["screens"][0]["label"] == "checkout" and state["screens"][0]["mobbin_url"] is None


def test_set_refuses_second_frame(make_run):
    run = make_run()
    cli("set", run, "01", "frame_id=AAA", "status=rendered", "--bump", "renders")
    screen = json.loads((run / "run.json").read_text())["screens"][0]
    assert (screen["frame_id"], screen["status"], screen["renders"]) == ("AAA", "rendered", 1)
    assert cli("set", run, "01", "frame_id=BBB", check=False).returncode != 0


def test_icon_check_board_is_separate_from_the_wireframe_board(make_run):
    run = make_run()
    cli("board", run, "--id", "BOARD")
    assert cli("board", run, "--id", "BOARD", "--swatch-board", "BOARD", check=False).returncode != 0
    cli("board", run, "--id", "BOARD", "--swatch-board", "SCRATCH")
    assert json.loads((run / "run.json").read_text())["swatch_board_id"] == "SCRATCH"


# ---------------------------------------------------------------- render, group, links

@pytest.fixture
def prepared_run(make_run):
    run = make_run()
    cli("board", run, "--id", "BOARD")
    draft = col(
        col(["w-shape", {"color": "light-gray", "deco": "fill",
                         "layout/style": {"height": 40, "margin": {"bottom": -40}}}],
            row(text("Card, title", flex=1),
                ["icon", {"icon-name": "favorite", "deco": "outline", "wf/color": "red",
                          "layout/style": {"width": 20, "height": 20}}]),
            **{"wf/group": "card"}),
        text("Footer"),
    )
    (run / "drafts" / "01.json").write_text(json.dumps(draft))
    return run


def test_prepare_prints_the_create_call_then_the_repair_call(prepared_run):
    first = json.loads(cli("prepare", prepared_run, "01").stdout)
    assert first["tool"] == "add_board_content"
    arguments = first["arguments"]
    assert (arguments["board_id"], arguments["title"], arguments["x"], arguments["y"]) == ("BOARD", "01 Screen 0",
                                                                                           216, 446)
    assert "wf/" not in json.dumps(first)
    cli("set", prepared_run, "01", "frame_id=FRAME")
    repair = json.loads(cli("prepare", prepared_run, "01").stdout)
    assert repair["tool"] == "wireframe_edit" and repair["arguments"]["target_id"] == "FRAME"


def test_prepare_places_frames_on_the_board_grid(make_run):
    run = make_run(sizes=[(1179, 2556)] * 7)
    cli("board", run, "--id", "BOARD")
    (run / "drafts" / "07.json").write_text(json.dumps(col(text("x"))))
    arguments = json.loads(cli("prepare", run, "07").stdout)["arguments"]
    assert (arguments["x"], arguments["y"]) == (wf.COLUMN_PITCH + 216, wf.ROW_PITCH + 446)


def test_postpass_maps_reverse_listing_to_groups_and_colors(prepared_run, tmp_path):
    cli("prepare", prepared_run, "01")
    cli("set", prepared_run, "01", "frame_id=FRAME")
    rows = [("text", "t2", "Footer", (0, 100, 50, 24)), ("icon", "i1", ""), ("text", "t1", "Card, title"),
            ("w-shape:rect", "s1", "", (0, 0, 392, 40))]
    (tmp_path / "l.json").write_text(listing("FRAME", rows))
    result = json.loads(cli("postpass", prepared_run, "01", tmp_path / "l.json").stdout)
    assert result["id"] == "BOARD"
    assert result["operations"] == [{"op": "update", "id": "i1", "color": "red"},
                                    {"op": "group", "ids": ["s1", "t1", "i1"]}]


@pytest.mark.parametrize("rows", [
    [("text", "t2", "Footer"), ("icon", "i1", ""), ("text", "t1", "Card, title")],
    [("text", "t2", "Footer"), ("icon", "i1", ""), ("text", "t1", "Other"), ("w-shape:rect", "s1", "")],
    [("group", "g", ""), ("text", "t2", "Footer")],
])
def test_postpass_refuses_listings_that_dont_match(prepared_run, tmp_path, rows):
    cli("prepare", prepared_run, "01")
    cli("set", prepared_run, "01", "frame_id=FRAME")
    (tmp_path / "l.json").write_text(listing("FRAME", rows))
    assert cli("postpass", prepared_run, "01", tmp_path / "l.json", check=False).returncode != 0


def test_postpass_needs_positions(prepared_run, tmp_path):
    cli("prepare", prepared_run, "01")
    cli("set", prepared_run, "01", "frame_id=FRAME")
    simple = ("type,id,parentId,text\ntext,t2,FRAME,Footer\nicon,i1,FRAME,\n"
              "text,t1,FRAME,Card, title\nw-shape:rect,s1,FRAME,\n")
    (tmp_path / "l.txt").write_text(simple)
    result = cli("postpass", prepared_run, "01", tmp_path / "l.txt", check=False)
    assert result.returncode != 0 and "detailed" in result.stderr


def test_postpass_keeps_floating_elements_above_groups(make_run, tmp_path):
    run = make_run()
    cli("board", run, "--id", "BOARD")
    surface = ["w-shape", {"color": "light-gray", "deco": "fill",
                           "layout/style": {"height": 100, "margin": {"bottom": -100}}}]
    draft = col(
        col(surface, text("Card one"), **{"wf/group": "card-1"}),
        ["w-button", {"text": "Keep going", "layout/style": {"margin": {"top": -30}}}],
        col(surface, text("Card two"), **{"wf/group": "card-2"}),
    )
    (run / "drafts" / "01.json").write_text(json.dumps(draft))
    cli("prepare", run, "01")
    cli("set", run, "01", "frame_id=FRAME")
    rows = [("text", "t2", "Card two", (0, 130, 200, 24)), ("w-shape:rect", "s2", "", (0, 130, 392, 100)),
            ("w-button", "b", "Keep going", (100, 90, 120, 32)),
            ("text", "t1", "Card one", (0, 0, 200, 24)), ("w-shape:rect", "s1", "", (0, 0, 392, 100))]
    (tmp_path / "l.json").write_text(listing("FRAME", rows))
    out = cli("postpass", run, "01", tmp_path / "l.json")
    assert json.loads(out.stdout)["operations"] == [{"op": "group", "ids": ["s1", "t1"]},
                                                    {"op": "group", "ids": ["b", "s2", "t2"]}]
    assert "floats over grouped content" in out.stderr


def test_links_go_under_each_frame(prepared_run, tmp_path):
    cli("set", prepared_run, "01", "frame_id=FRAME")
    (tmp_path / "f.txt").write_text("type,id,parentId,x,y,width,height,color,text\n"
                                    "frame,FRAME,,100,200,432,892,White,01 Screen 0\n")
    ops = json.loads(cli("links", prepared_run, tmp_path / "f.txt").stdout)["operations"]
    assert ops == [{"op": "add", "type": "link", "url": "https://mobbin.com/screens/00000000",
                    "text": "See screen on Mobbin.com", "x": 100.0, "y": 1112.0, "temp_id": "link01"}]


# ---------------------------------------------------------------- icons and grid

def test_icon_search_prefers_verified_names_and_hides_cloud_vendor_icons():
    names = [r["name"] for r in wf.search_icons("search")]
    assert names[0] == "zoom-2"
    assert not any(n.startswith(("azure-", "aws-")) for n in names)
    assert any("close" in c for r in wf.search_icons("close") for c in r["concepts"])


def test_icons_records_checked_names_and_refuses_misleading_ones(make_run):
    run = make_run()
    undescribed = next(n for n in wf.icon_index()["names"]
                       if n not in wf.icon_index()["descriptions"] and n not in wf.VERIFIED_ICONS)
    cli("icons", run, undescribed, "globe")
    assert json.loads((run / "run.json").read_text())["icons_checked"] == sorted([undescribed, "globe"])
    assert cli("icons", run, "plus", check=False).returncode != 0
    draft = col(["icon", {"icon-name": undescribed, "deco": "outline", "layout/style": {"width": 20, "height": 20}}])
    assert not any("no description" in w for w in wf.lint_layout(draft, [undescribed]).warnings)
    assert any("no description" in w for w in wf.lint_layout(draft).warnings)


def test_swatch_is_a_valid_layout():
    assert wf.lint_layout(json.loads(cli("swatch", "zoom-2", "favorite").stdout)).errors == []


def test_grid_writes_two_halves_at_frame_scale(make_run):
    run = make_run(sizes=[(1179, 2556)])
    out = json.loads(cli("grid", run, "01").stdout)
    assert [Path(p).name for p in out["grids"]] == ["01-top.png", "01-bot.png"]
    with Image.open(out["grids"][0]) as top:
        assert top.width == 60 + wf.CONTENT_W * wf.GRID_SCALE
        assert top.height == (380 + 54) * wf.GRID_SCALE
