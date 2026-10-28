# App Wireframe

Turn any app into editable wireframes in [Whimsical](https://whimsical.com). Name an
app and the skill pulls its key screens from [Mobbin](https://mobbin.com), or bring
your own screenshots.

```text
Make wireframes of Airbnb
```

That one line gets you a Whimsical board with up to 15 Airbnb screens, in the order
you'd move through the app, each rebuilt as a lo-fi iPhone wireframe. Cards, tab bars
and list rows are grouped, so you can drag them around and start editing right away.
Every wireframe links back to its screen on Mobbin.

This is a new project, and most of it was written by coding agents. We've used it at
Whimsical to wireframe 20 apps, but it hasn't been tested much with other agents or
setups. If something breaks, please [open an issue](https://github.com/WhimsicalCode/app-wireframe/issues).

## Two ways in

### Name an app, with the Mobbin MCP

This is the fastest path. Mobbin collects real screens from current iOS apps, and the
Mobbin MCP lets your agent search them the way you would on mobbin.com. The agent
looks up an app's sign-up, home, search, checkout and settings screens, picks the
ones that show how the app works, and downloads them at full resolution from the
links the MCP returns. A one-word prompt turns into a full board.

The skill only uses Mobbin's Standard Search, which doesn't spend
[AI credits](https://docs.mobbin.com/ai-credits).

With the Mobbin MCP you can also:

- wireframe a single screen from its Mobbin link (save it to your Mobbin account
  first) or from a description like "Spotify now playing"
- turn one of your Mobbin collections into a board, even one that mixes several apps

### Bring your own screenshots

Point the agent at a folder or a single image: your own app, your designs, or any
app whose screenshots you have the right to use. Any iPhone screenshot works and you
don't need a Mobbin account. Android and tablet screenshots get squeezed into an
iPhone frame, so they're not a good fit.

## What you'll get

A new board called `<App> iOS wireframes`, five wireframes per row, with a short
credit line above them that names the app and Mobbin. Before moving to the next
screen, the agent compares each wireframe with its screenshot, and a second agent
with no other context reviews it. The final report lists anything it couldn't get
right.

One screen takes a few minutes. A 15-screen app takes about an hour and a fair amount
of model usage, so try a single screen first.

## Requirements

- An agent that supports skills, remote MCP servers and images, such as
  [Claude Code](https://claude.com/claude-code). Results depend a lot on the model:
  use the strongest vision model you have.
- [uv](https://docs.astral.sh/uv/). It runs the skill's Python scripts and installs
  their dependencies the first time.
- A [Whimsical](https://whimsical.com) account, connected through the
  [Whimsical MCP](https://whimsical.com/learn/integrations/mcp).
- A [Mobbin](https://mobbin.com) Pro, Team or Enterprise plan, connected through the
  [Mobbin MCP](https://docs.mobbin.com/mcp/introduction), unless you only use your
  own screenshots. Mobbin's docs have setup guides for
  [Claude Code](https://docs.mobbin.com/mcp/clients/claude-code-cli),
  [Codex](https://docs.mobbin.com/mcp/clients/codex-cli),
  [Cursor](https://docs.mobbin.com/mcp/clients/cursor) and
  [other clients](https://docs.mobbin.com/mcp/clients/overview).

## Install

### Claude Code

```text
/plugin marketplace add WhimsicalCode/app-wireframe
/plugin install app-wireframe@app-wireframe
```

The plugin adds the skill and both MCP servers. Restart Claude Code, run `/mcp`, and
sign in to Whimsical and Mobbin. If you already had either server configured, you'll
see it twice; disable one in `/mcp`.

### Other agents

Copy [`skills/app-wireframe/`](skills/app-wireframe) into the folder your agent loads
skills from. Then add the two MCP servers, `https://mcp.whimsical.com/mcp` and
`https://api.mobbin.com/mcp`, using the setup guides from
[Whimsical](https://whimsical.com/learn/integrations/mcp) and
[Mobbin](https://docs.mobbin.com/mcp/clients/overview).

The skill hands each review to a subagent. If your agent doesn't have subagents, it
reviews the screen itself in a separate step and says so in its report.

## Use it

Start your agent in the folder where you want the working files, then ask in plain
language:

```text
Make wireframes of Duolingo
Wireframe this Mobbin screen: https://mobbin.com/screens/<id>
Wireframe the screens in https://mobbin.com/collections/<id>
Wireframe the Spotify now playing screen
Wireframe the screenshots in ./screens
```

The agent doesn't stop to confirm each step; it only stops when something blocks
it. It will probably ask permission for each tool the first time. Allowing the
Whimsical and Mobbin tools and `uv run` for the session keeps long runs moving.

Each run works in `wireframes/<Name>/`: screenshots, drafts and progress. If a run
stops halfway, ask again with the same app and it picks up where it left off.

### Put the screenshots on the board

The Whimsical MCP can't upload images yet, so this part is manual. Open the board and
drop every file from `wireframes/<Name>/screenshots/` onto empty canvas in one go.
Then ask:

```text
Arrange the screenshots on the Airbnb board
```

The agent works out which image belongs to which wireframe, puts each one next to
its wireframe at the same size, and moves its Mobbin link underneath.

## How it works

1. The agent searches the app's main journeys with the Mobbin MCP and picks up to 15
   distinct screens, or reads the screen or collection you linked. `mobbin_download.py`
   downloads the images and crops off Mobbin's footer bar. When it can't find the
   footer's edge exactly, it stops instead of guessing.
2. It looks at every screenshot once, then settles on one accent color, the
   components the screens share, and the icons it needs.
3. Then it builds one screen at a time. It measures the screenshot on a grid drawn in
   wireframe coordinates, writes the layout with shared component functions, checks
   it with `wireframes.py`, renders it and compares the result with the screenshot.
   A reviewer checks it again, up to three times per screen.
4. Last, it groups each screen's components, adds the Mobbin links and the credit
   line, and reports how each screen went.

The design rules live in
[`references/design.md`](skills/app-wireframe/references/design.md), and the layout
techniques that render well in Whimsical in
[`references/techniques.md`](skills/app-wireframe/references/techniques.md).

`wireframes.py` and `arrange.py` work offline: the agent calls Whimsical and Mobbin
and hands the results to the scripts. `mobbin_download.py` only fetches the image
links Mobbin returned, and only from Mobbin's servers.

## Using Mobbin screens

Screens on Mobbin belong to the companies that make those apps. Use them in line with
[Mobbin's terms](https://mobbin.com/terms). The skill keeps them in
`wireframes/<Name>/screenshots/` on your machine, credits the app on every board, and
links each wireframe to its screen on Mobbin. If you're working in a git repository,
keep `wireframes/` out of it.

## Privacy

The skill doesn't collect anything. Your agent talks to Whimsical and Mobbin through
their MCP servers, under their own privacy policies:
[Whimsical](https://whimsical.com/terms/privacy) and
[Mobbin](https://mobbin.com/privacy).

## Development

```text
skills/app-wireframe/
  SKILL.md                 the workflow the agent follows
  references/              design rules, layout techniques, review and arrange guides
  scripts/
    wireframes.py          run progress, draft checks, grouping, links, icons, grid
    arrange.py             places dropped screenshots next to their wireframes
    mobbin_download.py     downloads and crops the Mobbin screens of a shortlist
    icon_index.json        icon names, aliases and descriptions for the icon search
tests/                     tests for the scripts
.claude-plugin/            Claude Code plugin and marketplace manifests
.mcp.json                  the Whimsical and Mobbin MCP servers
```

```sh
uv run --group dev pytest
uv run --group dev ruff check .
claude plugin validate .
```

## License

[MIT](LICENSE)
