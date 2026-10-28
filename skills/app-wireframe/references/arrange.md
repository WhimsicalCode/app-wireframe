# Arrange screenshots next to their wireframes

The Whimsical MCP can't upload images, so the user drops the run's screenshots
onto the board themselves (all of `wireframes/<Name>/screenshots/*.png` at once,
anywhere on empty canvas). This puts each one next to its wireframe, at a
consistent size, with its "See screen on Mobbin.com" link underneath.

It only moves frames, moves and resizes the dropped images, and moves or adds
credit links. It never redesigns screens, creates groups, uploads or deletes.

`AR` below stands for `uv run <this skill's folder>/scripts/arrange.py`; type the
full command. It's offline like `wireframes.py`: you call Whimsical and pass the
results in.

Result: frames sit on a grid of 1439 px between columns and 1376 px between rows,
anchored on screen 01's frame (moving a frame moves its wireframe). Each
screenshot is 852 px tall, 132 px right of its frame and 4 px below the frame's
top, with its link 20 px below it, left-aligned. Pass `--keep-frames` to `plan`
only if the user wants their frames left exactly where they are.

## Steps

1. **Find the run.** The user names the app or gives the board link. Use the
   `wireframes/<Name>/` folder whose `wireframes.py status` shows that board. If
   it's ambiguous, ask which board before moving anything.
2. **Read the board.** `fetch` the board with
   `select_kinds: ["frame", "attachment", "image", "link"]`, `detail: "detailed"`,
   `limit: 200`, and save the whole result to `<run>/arrange/board.json`. Reads
   can lag recent changes: if fewer images show up than the user dropped, wait
   ~15 s and read again.
3. **Identify each screenshot.** The MCP doesn't return file names, so match by
   content:
   - `AR contact <run>` writes `<run>/arrange/contact.png`, every screenshot
     labelled with its screen key. Read it.
   - For each image ID in the listing, `fetch` with `image: true` and
     `crop_ids: [<image id>]`, and pick the matching key. Screens of one app can
     look alike (several map screens, two lists): compare titles, sheets, selected
     states and buttons, not just the overall look. If two stay ambiguous, open
     the full screenshots; if still unsure, ask the user.
   - If an image renders blank, wait and fetch it again; if it stays blank, the
     upload probably failed. Leave it out and tell the user to drop that file
     again.
   - Write `<run>/arrange/mapping.json`: `{"<image id>": "<screen key>", ...}`.
     Images that aren't this run's screenshots stay out of the mapping; then pass
     `--allow-unmapped` in the next step and tell the user.
4. **Plan.** `AR plan <run> <run>/arrange/board.json <run>/arrange/mapping.json`
   checks the mapping (each screen at most once, real image IDs, nothing landing
   on other content) and prints a summary line, then the edit. Read its notes. If
   it refuses, fix the mapping or tell the user; don't work around it.
5. **Apply once.** Pass the printed edit to `edit` unchanged. If the response maps
   new links (`linkNN=<id>`), record each with
   `wireframes.py set <run> NN link_id=<id>`.
6. **Verify.** Wait ~15 s, fetch the board as in step 2, save it to
   `<run>/arrange/board-after.json`, and run
   `AR verify <run> <run>/arrange/board-after.json`. If it fails right after the
   edit, wait and fetch once more. Never apply the edit a second time without
   reading what moved.
7. **Look.** Snapshot one row (`fetch` with `image: true` and `crop_ids` listing
   that row's frames and screenshots) and check each screenshot sits next to the
   wireframe of the same screen. Report the board link and anything left unplaced.

Running it again after the user drops a missing screenshot is safe: anything
already in place produces no operation.
