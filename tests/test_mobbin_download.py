import io
import json

import httpx
import mobbin_download as download
import pytest
from PIL import Image

ID = "fa8ec815-fc60-4287-91e7-e491e4448dc4"


def selected(url="https://mobbin.com/api/mcp/short/abc123"):
    return {"app_name": "Food app", "platform": "ios", "id": ID,
            "mobbin_url": f"https://mobbin.com/screens/{ID}", "image_url": url,
            "label": "Home feed", "reason": "Main entry point to discovery."}


def jpeg(image):
    buf = io.BytesIO()
    image.save(buf, format="JPEG")
    return buf.getvalue()


def with_footer(width=1179, height=2676, footer=120, wordmark=True, body="white"):
    image = Image.new("RGB", (width, height), body)
    image.paste((46, 46, 46), (0, height - footer, width, height))
    if wordmark:
        image.paste((250, 250, 250), (int(width * 0.79), height - 86, int(width * 0.93), height - 46))
    return image


@pytest.fixture
def plan(tmp_path):
    path = tmp_path / "Food app" / "plan.json"
    path.parent.mkdir()

    def write(screens=None):
        path.write_text(json.dumps({"app_name": "Food app", "platform": "ios",
                                    "screens": [selected()] if screens is None else screens}))
        return path
    write()
    return write


def client(data, redirect="https://bytescale.mobbin.com/screen.jpg"):
    def handle(request):
        if request.url.host == "mobbin.com":
            return httpx.Response(302, headers={"location": redirect})
        return httpx.Response(200, headers={"content-type": "image/jpeg"}, content=data)
    return httpx.Client(transport=httpx.MockTransport(handle))


def test_downloads_crops_and_records_provenance_without_overwriting(plan):
    path = plan()
    with client(jpeg(with_footer())) as http:
        target, items = download.download(path, client=http)
        assert target == path.parent / "screenshots"
        assert (items[0]["width"], items[0]["height"], items[0]["footer_pixels_removed"]) == (1179, 2556, 120)
        assert items[0]["crop_method"] == "detected"
        assert len(list(target.glob("*.png"))) == 1 and len(list((target / "_originals").glob("*.jpg"))) == 1
        with Image.open(target / items[0]["file"]) as cropped:
            assert cropped.size == (1179, 2556)
            assert cropped.getpixel((0, 2555)) == (255, 255, 255)
        selection = json.loads((target / "selection.json").read_text())
        assert selection["screens"][0]["mobbin_url"] == f"https://mobbin.com/screens/{ID}"
        with pytest.raises(FileExistsError):
            download.download(path, client=http)


def test_screens_without_a_footer_are_kept_whole(plan):
    with client(jpeg(Image.new("RGB", (1179, 2556), "white"))) as http:
        _, items = download.download(plan(), client=http)
    assert (items[0]["height"], items[0]["crop_method"]) == (2556, "none")


@pytest.mark.parametrize("screens", [
    [],
    [selected()] * 16,
    [{**selected(), "app_name": "Other"}],
    [selected("https://example.com/anything")],
    [selected("http://mobbin.com/api/mcp/short/abc")],
    [selected(), selected()],
])
def test_plan_must_hold_one_app_and_real_mobbin_results(plan, screens):
    with pytest.raises(ValueError):
        download.validated_plan(plan(screens))


def test_ambiguous_footer_fails_closed():
    with pytest.raises(ValueError, match="dark footer"):
        download.footer_boundary(Image.new("RGB", (1179, 2676), "white"))


def dark_app(footer=120, wordmark=True):
    # A dark tab bar meets the charcoal footer with too little contrast to detect the seam.
    return with_footer(1125, 2556, footer, wordmark, body=(34, 34, 46))


def test_low_contrast_footer_falls_back_to_the_standard_height():
    image = dark_app()
    with pytest.raises(ValueError, match="sharp, plausible"):
        download.footer_boundary(image)
    assert download.footer_crop(image) == (2436, "fixed_120")


@pytest.mark.parametrize("image", [dark_app(footer=140), dark_app(wordmark=False)])
def test_fallback_fails_closed_on_a_taller_footer_or_missing_wordmark(image):
    with pytest.raises(ValueError):
        download.footer_crop(image)


@pytest.mark.parametrize("data, redirect", [
    ("preview", "https://bytescale.mobbin.com/image.jpg"),
    ("full", "https://127.0.0.1/private"),
])
def test_preview_or_unsafe_redirect_leaves_no_partial_folder(plan, data, redirect):
    image = Image.new("RGB", (299, 678), "white") if data == "preview" else with_footer()
    path = plan()
    with client(jpeg(image), redirect) as http, pytest.raises(ValueError):
        download.download(path, client=http)
    assert not (path.parent / "screenshots").exists()
    assert not list(path.parent.glob(".download-*"))


def test_a_collection_may_mix_apps(plan, tmp_path):
    other = {**selected(), "id": "0b4f3a8e-2c1d-4e5f-9a6b-7c8d9e0f1a2b", "app_name": "Ride app",
             "mobbin_url": "https://mobbin.com/screens/0b4f3a8e-2c1d-4e5f-9a6b-7c8d9e0f1a2b"}
    path = plan([selected(), other])
    with pytest.raises(ValueError, match="collection"):
        download.validated_plan(path)
    data = json.loads(path.read_text())
    path.write_text(json.dumps({**data, "app_name": "Checkout ideas", "collection": True}))
    assert len(download.validated_plan(path)["screens"]) == 2
    with client(jpeg(with_footer())) as http:
        target, _ = download.download(path, client=http)
    assert json.loads((target / "selection.json").read_text())["apps"] == ["Food app", "Ride app"]
