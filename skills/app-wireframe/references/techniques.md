# Building wireframes with the Whimsical MCP

How wireframe layouts behave in Whimsical, and patterns that render well. Every
snippet below passes `WF check`. Read this before the first draft of a run.

## Canvas

- Frame `iphone-14`: 432×892 with status bar, bezel and home indicator drawn
  for you. Your root `div` fills a **392×792** content area that starts 80px
  below the frame top. Nothing clips: anything wider than 392 or taller than 792
  is drawn over the bezel or off the phone. Budget heights before drafting.
- 1 frame px ≈ 1 iOS point. For a source screenshot `W` px wide:
  `scale = 392 / W` (0.333 for 1179px, 0.304 for 1290px). A source element at
  `(x, y)` px lands at `(x·scale, y·scale - 54)` in the content area (54 ≈ the
  status bar). `WF grid` draws this conversion as a labelled grid over the
  screenshot: read measurements off it rather than eyeballing.
- Layout is flexbox. `div`s are invisible containers. Only `div`s can
  have children. Later siblings draw on top of earlier ones.

## Draft format

A draft is the hiccup JSON the MCP accepts, plus two draft-only keys that
`WF prepare` strips before rendering:

- `"wf/group": "card-1"` on a `div`: after rendering, every element inside it is
  grouped into one Whimsical group, so people can move the card as a unit. Use it
  for things a person would drag as one piece: cards, list rows, buttons with
  their icon, search bars, nav bars, headers, sheets, floating controls. One
  level only (no `wf/group` inside another), unique names, at least 2 elements.
- `"wf/color": "green"` on an `icon`: applied after rendering, because outline
  icons don't take `color` when created.

**Keep drafts compact.** Build them with a script from shared component
functions, and keep the output to one element per line. `padding` and `margin`
take a number for all sides, or an object with only the sides you need
(`{"bottom": -56}`). Leave out `gap: 0`. Repair a draft with small targeted edits
rather than rewriting it.

```json
["div", {"layout/style": {"flex-direction": "column", "gap": 12, "padding": {"top": 8, "left": 16, "right": 16}}},
  ["text", {"text": "**Featured**", "font-size": "l0", "text-align": "left", "layout/style": {"height": 28}}]]
```

## Rules the checker enforces (and why)

| Rule | Why |
| --- | --- |
| Every `div` sets `flex-direction`. | Removes ambiguity; the default is column. |
| Every `text` has `text-align` and `layout/style.height` = lines × line height (xs 16, s 20, m 24, l0 28, l1 36, l2 48). | Wireframe text is centered by default, and text without a height can take extra space in rows, pushing everything below it down. |
| Text inside a row has `width` or `flex: 1`. | Keeps its width predictable instead of a 200 px default. |
| No `margin` on `div`s. Use padding on the parent, or margin on a leaf. | Containers don't take margin. |
| No children on `w-shape` (or any element). | Only `div`s nest; use the layering pattern below. |
| Outline icons are `icon` with `deco: "outline"`, explicit width/height, no `color`. | `w-icon` draws filled glyphs; `icon` defaults to 96 px and takes its color after rendering. |
| `items` are plain strings. | Objects end up as label text. |
| After a closing `**` or `~~`, write `\u00a0` (non-breaking space) instead of a space. | A plain space right after the marker isn't rendered ("gone.This"). |
| `w-toggle` always has `state`. | Its default looks switched on. |
| Icon names exist in the icon set and aren't misleading (`plus`, `minus`, `phone`, `search`, `star`...). | Unknown names are replaced by the closest-spelled icon, and some common words name a different icon than you'd expect. |

It also warns about bordered image placeholders and outlined cards (see Style).

Font sizes in px: xs 13, s 15, m 18, l0 21, l1 27, l2 36. Average glyph width is
about 0.55 × size, so `m` fits roughly 38 characters per 392px line. Every text
box adds **8px of padding on each side**: two texts in a row look 16px further
apart than their `gap`. Truncate or wrap deliberately and set the height for the
lines you expect.

## Elements and the props they take

| Element | Props | Notes |
| --- | --- | --- |
| `text` | text, font-size, color, text-align | Markdown `**bold**`, `~~strike~~`. One color per text. |
| `w-shape` | color, deco (fill/outline/dashes), shape-type (rect/ellipse/pill), icon-name | Surfaces, image placeholders, circles. `icon-name` draws a centered icon. |
| `icon` | icon-name, deco | Outline icon. Color via `wf/color`. |
| `w-icon` | icon-name, color | Filled glyph. Use for filled/active states (active tab, filled heart). |
| `w-button` / `w-link` | text, color, deco (fill/outline/underline), size, state, icon-name, icon-placement, text-align | `align-self: stretch` for full width. Size `m` ≈ 40px tall, `l0` ≈ 48px. |
| `w-tag` | text, color, deco, size, icon-name, icon-placement | Badges, plates, chips that aren't buttons. Pill-shaped. |
| `w-input` / `w-textarea` | text (placeholder), label, state, icon-name, icon-placement | Label renders above. |
| `w-dropdown` | text (selected value), label, items, state | |
| `w-checkbox` / `w-radio-button` | items, label, state | One state for the whole group. |
| `w-toggle` | state (selected/unselected), color | |
| `w-stars` | pos, color, size | `pos` = stars / 5, whole stars only. |
| `w-progress-bar` / `w-slider` | pos (0-1), color, label | Delivery and upload progress, steps. |
| `w-divider` | color, deco | Full-width 1px line; `light-gray` for list hairlines. |
| `w-pattern` | color | Map texture. |
| `w-overlay` | color | Translucent dim layer: what's underneath stays visible, darkened. Modal backdrops. |
| `w-h-tabs` | items | No icons, no selected tab: avoid; build tabs by hand. |
| `link` | text, url | Board link with icon. |

There is no `w-image`, `w-map` or `w-avatar`; use the patterns below.

Palette: `white`, `light-gray` (pale surface), `silver` (quiet text, inactive
icons), `default` (dark slate: body text, dark buttons), `blue`, `whimsy-blue`
(indigo), `dark-purple`, `purple` (pink), `green` (renders pale mint),
`dark-green`, `brown`, `pale-red`, `red`, `orange`, `yellow`. Pick one accent
per app. Accent `w-shape` fills render as pale tints: put dark text on them, and
use `w-button`/`w-tag` when you need a solid accent.

## Style choices that keep boards light

- **Default to borderless fills.** Shapes, circles, pills and tags all render
  cleanly with `deco: "fill"`: `light-gray` on white, `white` on light-gray. Use
  an outline only when the source control has a visible border that matters
  (inputs, outlined buttons) or when a white surface floats over white content
  and would otherwise vanish (a floating nav pill on a white page).
- **Image placeholders are borderless fills**: `light-gray` fill on white,
  `white` fill on light-gray surfaces, with `icon-name: "image"`.
- **Pale chips and secondary buttons**: `w-button` with a `light-gray` fill
  renders as a heavier blue-gray. For pale pills use `w-tag` (`deco: "fill"`,
  `color: "light-gray"`, `size: "m"`, optional `icon-name`) or a layered
  `light-gray` pill shape with a centered label. Dark selected chips and dark
  buttons: `w-button`, `deco: "fill"`, `color: "default"`.
- **Buttons with an icon render wider than the layout expects**: give them an
  explicit `width`, or neighbours overlap.
- **Cards are filled, never outlined.** A white card with a hairline border in
  the source becomes a `light-gray` filled surface (or white on a light-gray
  page). Outlines are only for inputs, outlined buttons, chips and search bars.
- Dark source surfaces (promo bars, hero overlays) become `light-gray` fills
  with dark text.

## Patterns

### Surface with content on top (cards, sheets, banners)

The background is a leaf with `margin-bottom: -height`; the content follows and
draws over it. Give both the same height.

```json
["div", {"layout/style": {"flex-direction": "column"}, "wf/group": "promo"},
  ["w-shape", {"color": "light-gray", "deco": "fill", "layout/style": {"height": 56, "margin": {"bottom": -56}}}],
  ["div", {"layout/style": {"flex-direction": "row", "gap": 14, "height": 56, "align-items": "center", "padding": {"left": 16, "right": 16}}},
    ["icon", {"icon-name": "tag", "deco": "outline", "layout/style": {"width": 28, "height": 28}}],
    ["div", {"layout/style": {"flex-direction": "column", "flex": 1}},
      ["text", {"text": "**20% off this item in cart**", "font-size": "m", "text-align": "left", "layout/style": {"height": 24}}],
      ["text", {"text": "Applied at checkout. Ends Aug 4", "font-size": "s", "text-align": "left", "layout/style": {"height": 20}}]]]]
```

A small illustration inside a banner (a tag, a box, a gift) is better drawn as
the matching outline icon than as a tiny image placeholder.

### Card with image, overlays on the image, and copy

Card surface, then the image placeholder (also pulled up), then an overlay
column the image's height with rows for the corners, then the copy.

```json
["div", {"layout/style": {"flex-direction": "column", "width": 280, "flex-shrink": 0}, "wf/group": "card-1"},
  ["w-shape", {"color": "white", "deco": "fill", "layout/style": {"width": 280, "height": 224, "margin": {"bottom": -224}}}],
  ["w-shape", {"color": "light-gray", "deco": "fill", "icon-name": "image", "layout/style": {"width": 280, "height": 136, "margin": {"bottom": -136}}}],
  ["div", {"layout/style": {"flex-direction": "column", "justify-content": "space-between", "height": 136}},
    ["div", {"layout/style": {"flex-direction": "row", "justify-content": "space-between", "align-items": "flex-start", "padding": {"top": 12, "right": 12}}},
      ["w-tag", {"text": "Member deal", "color": "dark-purple", "deco": "fill", "size": "xs", "icon-name": "bold-add"}],
      ["icon", {"icon-name": "favorite", "deco": "outline", "layout/style": {"width": 24, "height": 24}}]],
    ["div", {"layout/style": {"flex-direction": "row", "justify-content": "flex-end", "padding": {"right": 12, "bottom": 12}}},
      ["w-tag", {"text": "10 min", "color": "white", "deco": "fill", "size": "s"}]]],
  ["div", {"layout/style": {"flex-direction": "column", "gap": 2, "padding": 12}},
    ["text", {"text": "**Restaurant name**", "font-size": "m", "text-align": "left", "layout/style": {"height": 24}}],
    ["div", {"layout/style": {"flex-direction": "row", "gap": 4}},
      ["text", {"text": "★ 4.5 Excellent", "font-size": "s", "color": "dark-green", "text-align": "left", "layout/style": {"width": 118, "height": 20}}],
      ["text", {"text": "(500+) · 0.2 mi", "font-size": "s", "color": "silver", "text-align": "left", "layout/style": {"flex": 1, "height": 20}}]],
    ["text", {"text": "~~£2.49~~\u00a0£0 delivery fee", "font-size": "s", "color": "red", "text-align": "left", "layout/style": {"height": 20}}]]]
```

A horizontal carousel is a row with `padding-left` 16 and `gap` 8 holding full
cards plus one **clipped** card whose width ends exactly at the content edge
(392 - 16 - 280 - 8 = 88 here). Build it from the same component as the full
cards, then cut it to look like the screenshot's slice: same image height and
fill, the start of any badge (`"Membe"`), and every copy line cut to what fits
mid-word (`"Store na"`, `"★ 4.9 Exce"`, `"$16.0"`). Drop the copy row's right
padding. Slivers narrower than ~40px still keep the image fill and the first
character or two of each line; they never become an empty strip. Product names on grid
and carousel cards keep their source weight (usually bold or medium).

### Circular icon button

```json
["div", {"layout/style": {"flex-direction": "column", "width": 40, "height": 40}, "wf/group": "basket-button"},
  ["w-shape", {"shape-type": "ellipse", "deco": "fill", "color": "light-gray", "layout/style": {"width": 40, "height": 40, "margin": {"bottom": -40}}}],
  ["div", {"layout/style": {"flex-direction": "row", "justify-content": "center", "align-items": "center", "height": 40}},
    ["icon", {"icon-name": "basket", "deco": "outline", "wf/color": "green", "layout/style": {"width": 22, "height": 22}}]]]
```

On a light-gray surface use a `white` fill. Outline the circle only when the
source shows a border and the button floats over white. A dark filled action in the source (dark cart button on a product tile) stays
dark: `"color": "default", "deco": "fill"` with a `white`-colored icon via
`wf/color`.

### Search bar

```json
["div", {"layout/style": {"flex-direction": "column"}, "wf/group": "search"},
  ["w-shape", {"shape-type": "pill", "deco": "fill", "color": "light-gray", "layout/style": {"height": 48, "margin": {"bottom": -48}}}],
  ["div", {"layout/style": {"flex-direction": "row", "align-items": "center", "gap": 10, "height": 48, "padding": {"left": 16, "right": 16}}},
    ["icon", {"icon-name": "zoom-2", "deco": "outline", "layout/style": {"width": 20, "height": 20}}],
    ["text", {"text": "Restaurants, groceries, dishes", "font-size": "m", "color": "silver", "text-align": "left", "layout/style": {"flex": 1, "height": 24}}]]]
```

Use an outlined white pill only when the source search bar is white with a
visible border. A plain form field: `w-input` with `label` and placeholder `text`.

### Two-tone lines ("Save $10 on orders over $35")

One `text` has one color. When part of a line is accented, make that part a
`w-tag` (when the source shows a pill) or a separate text, and pull the second
text back by its padding with `margin: {"left": -12}`.

```json
["div", {"layout/style": {"flex-direction": "row", "align-items": "center", "gap": 4}},
  ["w-tag", {"text": "Save $10", "color": "whimsy-blue", "deco": "fill", "size": "s"}],
  ["text", {"text": "on orders over $35", "font-size": "m", "color": "silver", "text-align": "left", "layout/style": {"flex": 1, "height": 24}}]]
```

### Category tabs with icons and a selected underline

Fixed-width columns so labels center; the selected tab gets a bold label, an
accent icon and a 3px accent bar drawn over the divider.

```json
["div", {"layout/style": {"flex-direction": "column"}, "wf/group": "category-tabs"},
  ["div", {"layout/style": {"flex-direction": "row", "padding": {"top": 12, "bottom": 8, "left": 4}}},
    ["div", {"layout/style": {"flex-direction": "column", "align-items": "center", "gap": 4, "width": 64}},
      ["icon", {"icon-name": "house", "deco": "outline", "wf/color": "green", "layout/style": {"width": 24, "height": 24}}],
      ["text", {"text": "**Home**", "font-size": "s", "text-align": "center", "layout/style": {"width": 64, "height": 20}}]],
    ["div", {"layout/style": {"flex-direction": "column", "align-items": "center", "gap": 4, "width": 96}},
      ["icon", {"icon-name": "cutlery", "deco": "outline", "layout/style": {"width": 24, "height": 24}}],
      ["text", {"text": "Restaurants", "font-size": "s", "text-align": "center", "layout/style": {"width": 96, "height": 20}}]]],
  ["w-divider", {}],
  ["w-shape", {"color": "green", "deco": "fill", "layout/style": {"width": 64, "height": 3, "margin": {"top": -3}}}]]
```

### Bottom tab bar

Same idea, five equal columns (`width` 78 or `flex: 1`), `padding-top` 8; the
active item uses `w-icon` (filled) or `wf/color` with the accent and a bold
label. Put a `w-divider` above it. Place it last in a root column whose earlier
content fills the remaining height (`flex: 1` on the content column) so it sits
at the bottom.

### Floating controls over content (pill nav, floating button)

Give the **last content leaf** a negative bottom margin equal to the overlap,
then add the floating row; it draws on top. Floating surfaces are white with an
outline so they hide what's underneath. Give floating controls a `wf/group`
together (a floating CTA with the nav row), so grouping can't bury them (see
"Stacking" below).

```json
["div", {"layout/style": {"flex-direction": "column", "gap": 14}},
  ["text", {"text": "A long description that continues under the floating navigation.", "font-size": "m", "text-align": "left", "layout/style": {"height": 96, "margin": {"bottom": -34}}}],
  ["div", {"layout/style": {"flex-direction": "row", "gap": 8}, "wf/group": "floating-nav"},
    ["div", {"layout/style": {"flex-direction": "column", "width": 232}},
      ["w-shape", {"shape-type": "pill", "deco": "outline", "color": "white", "layout/style": {"width": 232, "height": 56, "margin": {"bottom": -56}}}],
      ["div", {"layout/style": {"flex-direction": "row", "justify-content": "space-between", "align-items": "center", "height": 56, "padding": {"left": 28, "right": 28}}},
        ["w-icon", {"icon-name": "house", "color": "default", "layout/style": {"width": 24, "height": 24}}],
        ["icon", {"icon-name": "zoom-2", "deco": "outline", "layout/style": {"width": 24, "height": 24}}],
        ["icon", {"icon-name": "grid-interface", "deco": "outline", "layout/style": {"width": 24, "height": 24}}]]]]]
```

### Modal sheet over a dimmed screen

Draw the screen behind it first (root without padding, content column with a
fixed `height: 792`), then a `w-overlay` pulled up over it, then the sheet. The
overlay's top margin is -792 (cover everything); its bottom margin is
-(792 - sheet top), so the sheet starts where it does in the source.

```json
["div", {"layout/style": {"flex-direction": "column"}},
  ["div", {"layout/style": {"flex-direction": "column", "gap": 12, "padding": 16, "height": 792}},
    ["w-shape", {"color": "light-gray", "deco": "fill", "icon-name": "image", "layout/style": {"height": 220}}],
    ["text", {"text": "**Background screen**", "font-size": "l1", "text-align": "left", "layout/style": {"height": 36}}]],
  ["w-overlay", {"layout/style": {"height": 792, "margin": {"top": -792, "bottom": -592}}}],
  ["div", {"layout/style": {"flex-direction": "column", "padding": {"left": 16, "right": 16}}, "wf/group": "sheet"},
    ["w-shape", {"color": "white", "deco": "fill", "layout/style": {"height": 300, "margin": {"bottom": -300}}}],
    ["div", {"layout/style": {"flex-direction": "column", "gap": 8, "padding": 20, "height": 300}},
      ["text", {"text": "**Sheet title**", "font-size": "l0", "text-align": "left", "layout/style": {"height": 28}}],
      ["text", {"text": "Sheet content sits above the dim layer.", "font-size": "m", "text-align": "left", "layout/style": {"height": 24}}]]]]
```

Keep only the background elements that matter (hero image, top controls); they
read through the dim layer.

### Progress (delivery, steps)

Use `w-progress-bar` with `pos` for a filled track, with any endpoint markers
(carrier avatar, label icon) as small siblings in a row:

```json
["div", {"layout/style": {"flex-direction": "row", "align-items": "center", "gap": 8}},
  ["w-shape", {"shape-type": "ellipse", "color": "light-gray", "deco": "fill", "layout/style": {"width": 24, "height": 24}}],
  ["w-progress-bar", {"pos": 0.3, "color": "whimsy-blue", "layout/style": {"flex": 1}}]]
```

### Map with floating controls and a bottom sheet

`w-pattern` as the background leaf, an overlay column of the same height with
`justify-content: space-between` for top controls, a middle marker row and bottom
controls. The sheet follows as normal content on white, starting with a drag
handle (`w-shape` pill, light-gray, 40×5, `align-self: center`).

```json
["div", {"layout/style": {"flex-direction": "column"}},
  ["w-pattern", {"layout/style": {"height": 516, "margin": {"bottom": -516}}}],
  ["div", {"layout/style": {"flex-direction": "column", "justify-content": "space-between", "height": 516, "padding": {"top": 14, "right": 18, "bottom": 12, "left": 11}}},
    ["div", {"layout/style": {"flex-direction": "row", "justify-content": "space-between"}},
      ["w-button", {"text": "Menu", "icon-name": "menu-8", "deco": "outline", "color": "default", "size": "s", "layout/style": {"width": 92}}]],
    ["div", {"layout/style": {"flex-direction": "row", "padding": {"left": 158}}},
      ["icon", {"icon-name": "car-2", "deco": "outline", "layout/style": {"width": 28, "height": 28}}]],
    ["div", {"layout/style": {"flex-direction": "row"}},
      ["w-button", {"text": "Safety", "icon-name": "shield", "deco": "outline", "color": "default", "size": "s", "layout/style": {"width": 100}}]]]]
```

### Image placeholders and avatars

- Image: `["w-shape", {"color": "light-gray", "deco": "fill", "icon-name": "image", ...}]`
  (white fill when it sits on a light-gray surface).
- Hero images behind titles: a `light-gray` (or `white`) fill the size of the
  hero, with the title, rating and controls over it. Put the image icon only
  where it doesn't touch text: centered in the largest empty area of the hero
  (usually above the title). If there's no clear space, leave the icon out; the
  fill alone reads as an image. Never tuck it into a corner or under a line of
  text.
- Avatar: `["w-shape", {"shape-type": "ellipse", "color": "light-gray", "deco": "fill", "icon-name": "single-01", ...}]`.
- Badge on an avatar: layer a 16px `w-shape` ellipse in a row with
  `justify-content: flex-end` over the avatar (surface pattern).
- An image that overlaps the next row (a car photo beside a title): give it
  negative top/bottom margins so its row keeps the title's height.

### Chips, selections and steppers

- Option chips (sizes, filters): `w-button` with an explicit `width` each,
  matching the source's treatment. Outlined chips: `deco: outline`, `color:
  silver`; selected: `color: default` with bold text (or `deco: fill`,
  `color: default` when the source fills it dark). Pale filled chips: `w-tag`
  (see Style). Unavailable: `deco: fill`, `color: light-gray`, `~~XL~~`,
  `state: disabled`. Wrap to a second row explicitly; rows don't wrap for you
  unless you set `flex-wrap`.
- Quantity stepper: white outline pill surface 108×40 with `e-delete`, a centered
  count and `e-add`.
- Primary button: `w-button`, `deco: fill`, accent color, `size: l0`,
  `align-self: stretch`. Secondary dark: `color: default`. Text link: `w-link`.
  Filled secondary buttons in the source (gray pill buttons) stay filled: a
  `light-gray` pill shape with a centered label (layered), since a light-gray
  `w-button` renders heavier.

### Lists and settings rows

Row: `[icon] [text flex 1] [ctrl-right icon]`, `align-items: center`, fixed
height (48-56), `w-divider` between rows. Wrap each row in its own `wf/group`.
Use `["w-divider", {"color": "light-gray"}]` for the hairlines of typical iOS
lists. Section breaks between grouped lists: a 10px `light-gray` fill shape
across the full width (root padding 0).

## Icons

Use the outline `icon` element. Find names by meaning with the icon search, which
knows common concepts, their aliases and what each icon looks like:

```bash
WF icon "share" "notification bell" "external link"
```

Every name it returns exists in Whimsical's icon set, and the checker rejects
names that don't (they'd be replaced by the closest-spelled icon). Each result has
`looks_like` (what it draws), `concepts`, `checked_outline` (verified as an outline
icon) and `avoid` (a misleading name). Pick a `checked_outline` name when one
matches. Render a swatch only for names that aren't verified, once per app.

When a swatch or render response says `Auto-corrected icon name(s)`, the frame
shows the **corrected** icon while the swatch label still shows the name you
asked for. Treat the corrected name as what you got, and only keep names that
weren't corrected. Record names you checked by eye with `WF icons <run> name...`.

Misleading names: `plus` (a Google+ logo; use `e-add`), `minus` (use `e-delete`),
`phone` (a mobile phone; use `phone-2`), `search` (a magnifier in a box; use
`zoom-2`), `shield-check` (a cloud vendor logo; use `shield`), `star` (a star in a
box; write ratings as text: `★ 4.9`), `share` for the iOS share icon (use `upload`).

## Stacking and grouping

- Within a render, later siblings draw on top.
- A new group is drawn **above every ungrouped element**, in creation order.
  `WF postpass` creates groups in draft order and moves any ungrouped element
  that floats over grouped content into a later group (and tells you). Better:
  give floating elements a `wf/group` yourself.
- Board snapshots lag edits by ~10-15 s. Wait before the final look after the
  grouping, or a missing element won't show.

## Whimsical MCP behaviors to plan around

- `add_board_content` returns the frame's box but **not its ID**. Find it with
  `fetch {select_kinds: ["frame"]}` and the exact title.
- Reads can lag a write by several seconds (more on big boards). An empty or
  short result right after rendering means *wait and read again*, never *render
  again*.
- `fetch {scope: <frame id>, detail: "detailed", limit: 200}` lists a frame's
  elements with positions, in **reverse draft order**; `WF postpass` relies on
  both.
- `fetch {image: true, crop_ids: [<frame id>]}` is the reliable snapshot.
  Viewport snapshots sometimes drop elements.
- `wireframe_edit` with `layout` replaces all of a frame's elements (and their
  groups) and keeps the frame ID; `WF prepare` prints this call once a screen has
  a frame. For one-property fixes (a color, a label, a state), use operations
  mode (`operations: [{op: "update", id, ...}]`): a fraction of a full layout.
- The MCP reports one validation error per call: run the checker first.
- `edit` → `group` needs at least 2 elements and can't reference a group made in
  the same call; that's why groups are one level.
- `edit` → `add` `type: "link"` with `url`, `text`, `x`, `y` (top-left) makes a
  native link.
