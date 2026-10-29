import json

import httpx
import mobbin_link as link
import pytest

ID = "61a24089-f329-4527-befe-e281c5ac5423"
CARD = b"\x89PNG card"


def page(app="ZARA", patterns=("Product Detail",), elements=("Toolbar", "Carousel")):
    """A screen page as Mobbin serves it: an og:image card and the screen record escaped in the page data."""
    card = f"https://mobbin.com/api/og/screen?appName={app}&amp;appPlatform=ios&amp;appCategories=Shopping"
    record = json.dumps({"screen": {"id": ID, "screenElements": list(elements), "screenPatterns": list(patterns)}},
                        separators=(",", ":")).replace('"', '\\"')
    return (f'<meta property="og:image" content="{card}"/>'
            f'<script>self.__next_f.push([1,"{record}"])</script>').encode()


def client(body, card_redirect=None):
    """Mobbin as seen today: /screens/<id> redirects to /explore/screens/<id>, which serves the page."""
    def handle(request):
        path = request.url.path
        if path == f"/screens/{ID}":
            return httpx.Response(307, headers={"location": f"/explore/screens/{ID}"})
        if path == f"/explore/screens/{ID}":
            return httpx.Response(200, headers={"content-type": "text/html; charset=utf-8"}, content=body)
        if path == "/api/og/screen":
            if card_redirect:
                return httpx.Response(302, headers={"location": card_redirect})
            return httpx.Response(200, headers={"content-type": "image/png"}, content=CARD)
        return httpx.Response(404)
    return httpx.Client(transport=httpx.MockTransport(handle))


@pytest.mark.parametrize("text", [
    f"https://mobbin.com/screens/{ID}", f"https://mobbin.com/screens/{ID}?section=key_screens",
    f"mobbin.com/screens/{ID}", f"https://www.mobbin.com/explore/screens/{ID.upper()}/", f"  https://mobbin.com/screens/{ID}\n",
])
def test_reads_every_shape_of_screen_link(text):
    assert link.parse_link(text) == ("screen", "screens", ID)


@pytest.mark.parametrize("text", [
    f"https://example.com/screens/{ID}", f"https://mobbin.com.evil.io/screens/{ID}", "https://mobbin.com/screens/abc",
    f"https://mobbin.com/apps/{ID}", "Airbnb checkout",
])
def test_refuses_anything_but_a_mobbin_link(text):
    with pytest.raises(ValueError):
        link.parse_link(text)


def test_screen_link_gives_app_tags_query_and_card(tmp_path):
    with client(page()) as http:
        result = link.describe(f"https://mobbin.com/screens/{ID}?section=key_screens", tmp_path, http)
    assert result["app_name"] == "ZARA" and result["platform"] == "ios" and result["category"] == "Shopping"
    assert result["patterns"] == ["Product Detail"] and result["elements"] == ["Toolbar", "Carousel"]
    assert result["query"] == "ZARA product detail screen"
    assert result["mobbin_url"] == f"https://mobbin.com/screens/{ID}"
    assert (tmp_path / f"{ID}.png").read_bytes() == CARD and result["card"] == str(tmp_path / f"{ID}.png")


def test_untagged_screen_still_names_the_app(tmp_path):
    with client(page(app="WHOOP", patterns=(), elements=())) as http:
        result = link.describe(f"https://mobbin.com/screens/{ID}", tmp_path, http)
    assert (result["app_name"], result["patterns"], result["query"]) == ("WHOOP", [], "WHOOP screen")


@pytest.mark.parametrize("body", [b"<html>Not found</html>", b""])
def test_unreadable_page_keeps_kind_and_id_for_the_fallback(tmp_path, body):
    with client(body) as http:
        result = link.describe(f"https://mobbin.com/screens/{ID}", tmp_path, http)
    assert result["id"] == ID and result["page"].startswith("unreadable") and "app_name" not in result


def test_card_never_leaves_mobbin(tmp_path):
    with client(page(), card_redirect="https://example.com/card.png") as http:
        result = link.describe(f"https://mobbin.com/screens/{ID}", tmp_path, http)
    assert result["app_name"] == "ZARA" and result["card"] is None and not list(tmp_path.iterdir())


def test_collection_links_are_parsed_without_a_request(tmp_path):
    def refuse(request):
        raise AssertionError("no request expected")
    with httpx.Client(transport=httpx.MockTransport(refuse)) as http:
        result = link.describe(f"https://mobbin.com/collections/{ID}", tmp_path, http)
    assert result == {"kind": "collection", "id": ID, "mobbin_url": f"https://mobbin.com/collections/{ID}"}
