# Design rules: a lo-fi wireframe from a screenshot

Read by the designer and the reviewer. The screenshot decides content, structure,
state and relative emphasis; these rules decide how that's expressed in lo-fi. The
goal is a clear, consistent, **editable** abstraction of the interface: not a
restyling of the app, and not a pixel copy.

## Structure first

- Infer groups before drawing: containment, alignment, proximity and role. Write
  the component tree before any layout.
- A text stack (title, rating, meta) is a sibling of an action cluster (save,
  share), not part of it. Buttons beside a title must not stretch the gap between
  the title and its rating.
- Each group has its own spacing. Keep labels with their fields, badges with their
  products, prices with their summaries, and actions with the objects they affect.
  Spacing inside a group differs from spacing between groups.
- Keep reading order, relative sizes, line counts, density, and the alignment of
  comparable edges. Size controls from the source's proportions: a small badge or
  text action isn't a primary button.

## Content

- Keep every functional element and meaningful state: selected tab or chip,
  disabled or unavailable options, filled vs empty icons, toggles, counts,
  struck-through old prices, progress, badges.
- Replace brand, product, people and place names with **descriptive generic
  names** that fit: "Crew neck tee", "Shampoo bar", "Scented candle, large" rather
  than a wall of "Product name". Match the source's length and line count, and
  truncate exactly where the source truncates ("Rice water shampoo b…"). Replace a
  name whole, never half ("Product name Shampoo Bar for Growth"). People and places
  stay neutral ("Driver name", "Street address"). The app's own sub-brands,
  membership tiers and campaign names count as brand names: they become
  "Membership", "Seasonal deals", "Family meals". Keep functional copy as it is
  ("Add to cart", "Delivery fee", "Sort"), along with category names and search
  terms. Plain, concise wording; no filler, no em dashes, no emoji.
- One image placeholder per image region in the source; a collage is one
  placeholder. Don't transcribe logos or text printed inside photos. Keep
  functional overlays on images (save heart, badges, duration pills) as separate
  elements.
- Avatars and store logos become circular avatar placeholders. Maps become a map
  pattern. Never replace a functional control with an image.
- Keep floating calls to action (a floating "Continue", cart or compose button)
  and modal context: a sheet over a dimmed screen keeps the dim layer and a hint
  of the screen behind it.
- Keep meaningful partial content, and make it look like the screenshot: a
  carousel's clipped next card shows the same slice the source shows (the image
  sliver, the start of its badge, each copy line cut at the screen edge mid-word),
  not an empty strip and not a narrow complete card. A section header or chip
  peeking at the edge stays.
- Ignore watermarks, the status bar and the home indicator: the frame draws the
  device.

## Lo-fi style

- Simple rectangular, pale neutral **filled** surfaces for cards, sheets and
  sections; the fill groups a card's header, content and actions. No decorative
  outlines around cards, thumbnails or sub-groups: a white card with a hairline
  border in the source becomes a light-gray filled surface. Outlines are for
  fields and controls whose role needs them (inputs, outlined buttons, chips,
  search bars).
- Image placeholders are borderless pale fills with an image icon, never outlined
  boxes, and stand out from the surface they sit on.
- Default to borderless fills for shapes, circles, pills and chips. Outlines only
  where the source's border carries meaning, or where a white surface floats over
  white content.
- No corner radii or shadows on cards. Circles stay for avatars and circular
  buttons, pills for pill-shaped controls (search bars, chips, segmented controls).
- A small neutral palette plus **one accent color** for the app, reused on every
  screen (selected states, primary buttons, key icons). Dark source panels may
  become light neutral surfaces: keep the separation between layers, not the color
  polarity. Dark text on pale fills.
- A small, consistent type scale: a few heading sizes, normal body, quieter
  metadata. Badges and price tags stay secondary to content.
- Native buttons for buttons, with clear primary vs secondary emphasis. Keep the
  source's treatment: filled stays filled (a dark cart button stays dark, gray pill
  buttons stay gray fills), outlined stays outlined. Text actions stay text or
  links.
- Progress (delivery, steps, uploads) is a progress bar, not a row of blocks.
- Outline icons that mean the same thing as the source icon: a share arrow, a
  notification bell and a search glyph are different things. Never emoji or a
  convenient stand-in.
- Don't invent decoration or fake effects (blur, translucency, gradients).
  Floating controls get a white surface so content underneath stays hidden.

## Consistency across an app

Reuse the same navigation bars, headers, card components, sizes and accent on
every screen of an app. Reuse a shared component's code from an earlier draft
rather than redrawing it.

## Judging a result

A **major** finding changes grouping, layering, affordance, reading order, state or
meaningful relative scale: a missing or invented control, a lost containing
surface, metadata more prominent than the title, a floating control covering
something that's unobstructed in the source, content running off the frame, an
icon with the wrong meaning. A **minor** finding is cosmetic: a few pixels of
spacing, pill vs rectangle on a tag, a different glyph with the same meaning.
Generic copy is expected.
