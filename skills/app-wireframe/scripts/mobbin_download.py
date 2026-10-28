# /// script
# requires-python = ">=3.11"
# dependencies = ["httpx>=0.27,<1", "pillow>=11,<13"]
# ///
"""Download the screens of a shortlist built from Mobbin MCP results, and crop Mobbin's footer.

  uv run scripts/mobbin_download.py wireframes/<App>/plan.json

The plan holds metadata copied from Mobbin MCP results (screen IDs, links, image URLs);
this script never searches Mobbin or invents IDs. It checks the plan, downloads each
full-resolution image, removes the Mobbin footer bar, and writes lossless PNGs plus a
`selection.json` with each screen's Mobbin link. Originals are kept in `_originals/`.
It fails closed rather than guess a crop, and never overwrites an existing folder.
"""

import argparse
import hashlib
import io
import json
import re
import shutil
import tempfile
from pathlib import Path
from urllib.parse import urlparse
from uuid import UUID

import httpx
from PIL import Image

MAX_SCREENS = 15
MAX_IMAGE_BYTES = 25 * 1024 * 1024
MAX_REDIRECTS = 5
# Mobbin's iOS exports end with a 120 px charcoal footer bar carrying the Mobbin wordmark.
FIXED_FOOTER_HEIGHT = 120


def safe_name(name):
    text = re.sub(r"[^\w -]", "", name, flags=re.UNICODE).strip().replace("/", "")
    text = re.sub(r"\s+", " ", text)
    if text in ("", ".", "..") or len(text) > 70:
        raise ValueError("App/label must be a short safe name.")
    return text


def mobbin_https(url):
    parsed = urlparse(url) if isinstance(url, str) else None
    return bool(parsed and parsed.scheme == "https" and parsed.hostname
                and (parsed.hostname == "mobbin.com" or parsed.hostname.endswith(".mobbin.com"))
                and not parsed.username and not parsed.password and parsed.port is None)


def validate_image_url(url):
    if not mobbin_https(url):
        raise ValueError("Expected the image_url of a Mobbin MCP result (an https Mobbin link); "
                         "don't substitute inline previews or other images.")


def validate_redirect(url):
    if not mobbin_https(url):
        raise ValueError("Mobbin image redirected outside HTTPS Mobbin hosts; inspect rather than fetching.")


def validated_plan(path):
    plan = json.loads(path.read_text())
    if not isinstance(plan, dict) or not isinstance(plan.get("app_name"), str) or not plan["app_name"].strip():
        raise ValueError("Plan must have an app_name and selected screens.")
    app = plan["app_name"]
    # A collection may mix apps: then app_name names the collection and each screen keeps its own app.
    mixed = bool(plan.get("collection"))
    if plan.get("platform") != "ios":
        raise ValueError("Only iOS screens are supported.")
    screens = plan.get("screens")
    if not isinstance(screens, list) or not 1 <= len(screens) <= MAX_SCREENS:
        raise ValueError("Select between 1 and 15 screens, not more and not empty.")
    ids = set()
    for screen in screens:
        if not isinstance(screen, dict):
            raise ValueError("Screen must contain metadata from a real Mobbin search result.")
        try:
            ident = str(UUID(screen["id"]))
            label = safe_name(screen["label"])
            reason = screen["reason"]
        except (KeyError, TypeError, ValueError) as error:
            raise ValueError("Each screen needs a UUID, a label and a selection reason.") from error
        if ident != screen["id"] or ident in ids:
            raise ValueError("Screen IDs must be distinct canonical Mobbin UUIDs.")
        ids.add(ident)
        if not isinstance(reason, str) or not reason.strip() or len(reason) > 500:
            raise ValueError("Each screen needs a brief selection reason.")
        if screen.get("platform") != "ios" or not isinstance(screen.get("app_name"), str):
            raise ValueError("Each screen needs its iOS app_name from the Mobbin result.")
        if not mixed and screen["app_name"] != app:
            raise ValueError("All screens must belong to the plan's app (set \"collection\" for a mixed collection).")
        if screen.get("mobbin_url") != f"https://mobbin.com/screens/{ident}":
            raise ValueError("Screen's Mobbin link does not match its ID.")
        validate_image_url(screen.get("image_url"))
        screen["label"] = label
    return plan


def fetch_image(client, url):
    validate_image_url(url)
    for _ in range(MAX_REDIRECTS + 1):
        validate_redirect(url)
        with client.stream("GET", url, follow_redirects=False) as response:
            if response.status_code in (301, 302, 303, 307, 308):
                location = response.headers.get("location")
                if not location:
                    raise ValueError("Mobbin returned a redirect without Location.")
                url = str(response.url.join(location))
                continue
            response.raise_for_status()
            if response.headers.get("content-type", "").split(";")[0] not in ("image/jpeg", "image/png", "image/webp"):
                raise ValueError("Mobbin response is not an image; source link may be expired.")
            chunks = bytearray()
            for chunk in response.iter_bytes():
                chunks.extend(chunk)
                if len(chunks) > MAX_IMAGE_BYTES:
                    raise ValueError("Mobbin image exceeds the 25 MB safety limit.")
            data = bytes(chunks)
            with Image.open(io.BytesIO(data)) as image:
                image.verify()
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in ("JPEG", "PNG", "WEBP") or image.width < 450 or image.height < 900:
                    raise ValueError("Not a full-resolution mobile screenshot; do not save a preview.")
                return data, image.format, image.size
    raise ValueError("Too many Mobbin redirects.")


def color_distance(a, b):
    return sum(abs(x - y) for x, y in zip(a, b))


def has_wordmark(rgb, seam):
    # The Mobbin wordmark occupies the right of the footer. This is a graphical
    # sanity check, not OCR. Do not crop on background colour alone.
    width, height = rgb.size
    bright = sum(
        min(rgb.getpixel((x, y))) > 185
        for y in range(seam + 18, height - 12, 4)
        for x in range(int(width * 0.77), int(width * 0.98), 4)
    )
    return bright >= 40


def has_footer(image):
    """True when the bottom corners show Mobbin's charcoal bar; screens without it are kept whole."""
    rgb = image.convert("RGB")
    width, height = rgb.size
    corners = [rgb.getpixel((x, height - 3)) for x in (0, width - 1)]
    return all(25 <= c <= 70 for color in corners for c in color)


def footer_crop(image):
    """Return (seam, method). Detect the seam; fall back to a verified fixed height.

    Dark apps can put a bar just above the footer that's too close to its
    charcoal for edge detection. Then try a cut at exactly FIXED_FOOTER_HEIGHT,
    accepted only if the footer colour starts right below it, the row above it
    is clearly not footer colour (so a taller footer would be rejected), and the
    wordmark is there. Anything else fails closed with the detector's error.
    """
    try:
        return footer_boundary(image), "detected"
    except ValueError as detect_error:
        rgb = image.convert("RGB")
        width, height = rgb.size
        seam = height - FIXED_FOOTER_HEIGHT
        edge_x = (0, max(1, width // 100), width // 2, width - 1)
        base = rgb.getpixel((0, height - 3))
        # Rows 0-1 of the footer blend with the UI above (JPEG); from row 2 it's flat.
        footer_flat = all(color_distance(rgb.getpixel((x, y)), base) <= 12
                          for y in range(seam + 2, seam + 9) for x in edge_x)
        ui_above = all(color_distance(rgb.getpixel((x, seam - 1)), base) >= 15 for x in edge_x)
        if footer_flat and ui_above and has_wordmark(rgb, seam):
            return seam, f"fixed_{FIXED_FOOTER_HEIGHT}"
        raise detect_error


def footer_boundary(image):
    """Locate the exact Mobbin footer seam; never infer a crop from a fixed pixel count.

    Current Mobbin exports have a charcoal (#2e2e2e) full-width bar with white
    branding at the bottom. If the image format/design changes, fail closed.
    """
    rgb = image.convert("RGB")
    width, height = rgb.size
    if width < 450 or height < 900:
        raise ValueError("Screenshot is too small for reliable footer detection.")
    edge_x = (0, max(1, width // 100), width // 2, width - 1)
    baseline = [rgb.getpixel((x, height - 3)) for x in (0, width - 1)]
    if any(not 25 <= c <= 70 for color in baseline for c in color):
        raise ValueError("Mobbin dark footer is not visible at both bottom corners.")
    if any(max(color) - min(color) > 8 for color in baseline):
        raise ValueError("Bottom edge does not match the neutral Mobbin footer.")
    if sum(abs(a - b) for a, b in zip(*baseline)) > 12:
        raise ValueError("Bottom corners disagree; footer is not full-width.")
    base = baseline[0]
    low = height - min(width // 3, height // 5)
    high = height - max(55, width // 20)
    candidates = []
    for y in range(low, high):
        changes = [sum(abs(a - b) for a, b in zip(rgb.getpixel((x, y - 1)), rgb.getpixel((x, y))))
                   for x in edge_x]
        candidates.append((min(changes), sum(changes) / len(changes), y))
    _, score, seam = max(candidates)
    if score < 55 or seam < 1 or height - seam > width // 4:
        raise ValueError("Cannot locate a sharp, plausible full-width footer boundary.")
    for x in edge_x:
        below = rgb.getpixel((x, seam + 12))
        above = rgb.getpixel((x, seam - 12))
        if sum(abs(a - b) for a, b in zip(below, base)) > 18:
            raise ValueError("Region below seam does not match the Mobbin footer background.")
        if sum(abs(a - b) for a, b in zip(above, base)) < 30:
            raise ValueError("Region above seam resembles footer; cannot prove UI boundary.")
    if not has_wordmark(rgb, seam):
        raise ValueError("Mobbin branding was not found in the footer; inspect the source.")
    return seam


def download(plan_path, target=None, client=None):
    plan = validated_plan(plan_path)
    app = plan["app_name"]
    target = Path(target) if target else Path(plan_path).parent / "screenshots"
    if target.exists() or target.is_symlink():
        raise FileExistsError(f"{target} already exists; keeping it. Reuse it, or choose another folder.")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".download-", dir=target.parent))
    owns_client = client is None
    if owns_client:
        client = httpx.Client(timeout=30, trust_env=False)
    try:
        saved = []
        for i, screen in enumerate(plan["screens"], 1):
            data, image_format, (width, height) = fetch_image(client, screen["image_url"])
            ext = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}[image_format]
            name = f"{i:02d} - {screen['label'][:45].strip()} - {screen['id'][:8]}{ext}"
            originals = staging / "_originals"
            originals.mkdir(exist_ok=True)
            original_name = f"{i:02d} - {screen['id'][:8]}{ext}"
            (originals / original_name).write_bytes(data)
            with Image.open(io.BytesIO(data)) as image:
                seam, crop_method = footer_crop(image) if has_footer(image) else (height, "none")
                # Lossless PNG avoids introducing any more compression into UI pixels.
                cropped = image.crop((0, 0, width, seam))
                output = io.BytesIO()
                cropped.save(output, format="PNG")
            name = f"{i:02d} - {screen['label'][:45].strip()} - {screen['id'][:8]}.png"
            cropped_bytes = output.getvalue()
            (staging / name).write_bytes(cropped_bytes)
            saved.append({**screen, "file": name, "width": width, "height": seam,
                          "original_file": f"_originals/{original_name}",
                          "original_height": height, "footer_pixels_removed": height - seam,
                          "crop_y": seam, "crop_method": crop_method,
                          "original_sha256": hashlib.sha256(data).hexdigest(),
                          "sha256": hashlib.sha256(cropped_bytes).hexdigest()})
        (staging / "selection.json").write_text(json.dumps({
            "app_name": app, "platform": "ios", "source": "Mobbin MCP", "collection": bool(plan.get("collection")),
            "apps": sorted({screen["app_name"] for screen in saved}), "screens": saved,
        }, indent=2) + "\n")
        # Move only after every image and the provenance manifest passed validation.
        # No merge, overwrite, or cleanup of an existing app's screenshots.
        if target.exists() or target.is_symlink():
            raise FileExistsError(f"{target} appeared during download; refusing to overwrite it.")
        staging.rename(target)
        return target, saved
    finally:
        if owns_client:
            client.close()
        if staging.exists():
            shutil.rmtree(staging)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("plan", type=Path, help="JSON shortlist copied from Mobbin MCP results")
    parser.add_argument("--out", type=Path, help="screenshot folder to create (default: screenshots/ next to the plan)")
    args = parser.parse_args()
    target, screens = download(args.plan, args.out)
    print(json.dumps({"folder": str(target), "screen_count": len(screens),
                      "manifest": str(target / "selection.json")}, indent=2))


if __name__ == "__main__":
    main()
