# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx>=0.27,<1"]
# ///
"""Read a Mobbin link the user pasted, so the agent can find that screen with the Mobbin MCP.

  uv run scripts/mobbin_link.py 'https://mobbin.com/screens/<id>'

The Mobbin MCP can't look a screen up by its ID. This reads the screen's public page for what
a link preview shows: the app, its platform and category, the screen's patterns and UI elements
when Mobbin has tagged them, and the preview card, saved as an image so the agent can see the
screen. It prints a search query built from them. The screenshot itself is still downloaded from
a Mobbin MCP result's image_url, never from the page.

Collection and flow links are only parsed. If the page can't be read, it still prints the link's
kind and ID, with the reason under `page`, so the agent can fall back to the user's saved screens.
"""

import argparse
import html
import json
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from uuid import UUID

import httpx

KINDS = {"screens": "screen", "flows": "flow", "collections": "collection"}
LINK_PATH = re.compile(r"^/(?:explore/)?(screens|flows|collections)/([0-9a-fA-F-]{36})/?$")
OG_IMAGE = re.compile(r'<meta property="og:image" content="([^"]+)"')
CARD_TYPES = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}
MAX_PAGE_BYTES = 5 * 1024 * 1024
MAX_CARD_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 5
USER_AGENT = "app-wireframe (+https://github.com/WhimsicalCode/app-wireframe)"


def parse_link(text):
    """Kind, Mobbin path segment and ID of a link, with or without https:// and a query string."""
    text = text.strip()
    parsed = urlparse(text if "://" in text else f"https://{text}")
    match = LINK_PATH.match(parsed.path)
    if parsed.hostname not in ("mobbin.com", "www.mobbin.com") or not match:
        raise ValueError("Expected a Mobbin screen, flow or collection link, like https://mobbin.com/screens/<id>.")
    try:
        ident = str(UUID(match[2]))
    except ValueError:
        raise ValueError("The link's ID is not a valid Mobbin ID.") from None
    return KINDS[match[1]], match[1], ident


def clean(text, limit=80):
    """Page text is data: one line, no control characters, short."""
    return re.sub(r"\s+", " ", re.sub(r"[\x00-\x1f\x7f]", " ", text)).strip()[:limit]


def mobbin_https(url):
    return (url.scheme == "https" and url.port is None and not url.userinfo
            and (url.host == "mobbin.com" or url.host.endswith(".mobbin.com")))


def get(client, url, types, limit):
    """GET a Mobbin URL, following redirects only within Mobbin. Returns the content type and body."""
    url = httpx.URL(url)
    for _ in range(MAX_REDIRECTS + 1):
        if not mobbin_https(url):
            raise ValueError("Mobbin redirected outside its https hosts.")
        with client.stream("GET", url, follow_redirects=False) as response:
            if response.is_redirect:
                url = response.url.join(response.headers["location"])
                continue
            if response.status_code != 200:
                raise ValueError(f"Mobbin returned HTTP {response.status_code}.")
            content_type = response.headers.get("content-type", "").split(";")[0]
            if content_type not in types:
                raise ValueError(f"Mobbin returned {content_type or 'no content type'}.")
            body = bytearray()
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body) > limit:
                    raise ValueError("Mobbin's response is larger than expected.")
            return content_type, bytes(body)
    raise ValueError("Too many Mobbin redirects.")


def screen_tags(page, ident, field):
    """A tag list (screenPatterns, screenElements) from the screen record the page embeds, or []."""
    start = page.find(f'\\"screen\\":{{\\"id\\":\\"{ident}\\"')
    match = re.search(rf'\\"{field}\\":(\[[^\]]*\])', page[start:start + 5000]) if start >= 0 else None
    try:
        tags = json.loads(match[1].replace('\\"', '"')) if match else []
    except json.JSONDecodeError:
        return []
    return [clean(tag) for tag in tags if isinstance(tag, str) and tag.strip()]


def read_screen(client, ident, card_dir):
    _, body = get(client, f"https://mobbin.com/screens/{ident}", ("text/html",), MAX_PAGE_BYTES)
    page = body.decode("utf-8", "replace")
    og_image = OG_IMAGE.search(page)
    card_url = html.unescape(og_image[1]) if og_image else ""
    params = {key: clean(values[0]) for key, values in parse_qs(urlparse(card_url).query).items()}
    if not params.get("appName"):
        raise ValueError("The page doesn't name the app; Mobbin may have changed its pages.")
    patterns = screen_tags(page, ident, "screenPatterns")
    screen = {"app_name": params["appName"], "platform": params.get("appPlatform", "").lower(),
              "category": params.get("appCategories", ""), "patterns": patterns,
              "elements": screen_tags(page, ident, "screenElements"),
              "query": " ".join([params["appName"], *[p.lower() for p in patterns[:1]], "screen"]), "card": None}
    # The card is Mobbin's link preview: a small picture to recognise the screen, never a source.
    try:
        content_type, card = get(client, card_url, CARD_TYPES, MAX_CARD_BYTES)
        card_dir.mkdir(parents=True, exist_ok=True)
        path = card_dir / f"{ident}{CARD_TYPES[content_type]}"
        path.write_bytes(card)
        screen["card"] = str(path)
    except (httpx.HTTPError, ValueError):
        pass
    return screen


def describe(link, card_dir="wireframes/.mobbin-cards", client=None):
    kind, segment, ident = parse_link(link)
    result = {"kind": kind, "id": ident, "mobbin_url": f"https://mobbin.com/{segment}/{ident}"}
    if kind != "screen":
        return result
    owns_client = client is None
    if owns_client:
        client = httpx.Client(timeout=20, trust_env=False, headers={"user-agent": USER_AGENT})
    try:
        result.update(read_screen(client, ident, Path(card_dir)))
    except (httpx.HTTPError, ValueError) as error:
        result["page"] = f"unreadable: {error}"
    finally:
        if owns_client:
            client.close()
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("link", help="a Mobbin screen, flow or collection link")
    parser.add_argument("--card-dir", default="wireframes/.mobbin-cards",
                        help="where to save the screen's preview card (default: %(default)s)")
    args = parser.parse_args()
    try:
        result = describe(args.link, args.card_dir)
    except ValueError as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
