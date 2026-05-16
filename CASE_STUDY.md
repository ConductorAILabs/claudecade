# Claudecade

**The terminal arcade you launch from inside Claude Code.**

Seven complete games, one shared engine, zero dependencies, a real Postgres
leaderboard — all running in the same window where you write code.

[claudecade.games](https://claudecade.games)

---

## TL;DR

A Python curses arcade with seven full games, a 1,400-line shared engine
that fits in a single file, an MCP server that lets Claude install and
launch it with one prompt, and a live global leaderboard. Built end-to-end
in pair-programming sessions with Claude Code — designed, tuned, and
shipped without leaving the terminal.

---

## The Hook

Why do work when you can play games in your Claude terminal instead?

Claudecade is part product, part demo, part love letter to the arcade
era of pick-up-and-play. The arcade installs with a single command, the
games run inside a tmux split next to your editor, and a real
Postgres-backed leaderboard tracks every score across every player. No
launcher download. No package manager. Just `python3 claudcade.py`.

---

## By the Numbers

| | |
|---|---|
| Games shipped | **7** |
| Genres covered | shoot-'em-up · run-and-gun · fighting · platformer · racing · creature-RPG · JRPG |
| Source lines (Python) | **~9,000** |
| Engine file | **1 file · ~1,400 lines** |
| Runtime dependencies | **0** (`curses` ships with Python) |
| MCP tools exposed | **6** (setup, list, leaderboard, submit, docs, scaffold) |
| Sites deployed | **1** marketing + leaderboard + zip download (Netlify, Postgres on Neon) |
| Spells in the JRPG | **26** |
| Fighters in the brawler | **4** |
| Tests | round-trip save · offline score contract · engine math · 5 passing |

---

## The Product

**Seven games, one engine, one keystroke to launch.**

- **C-TYPE** — vertical-scroll space shooter with a chargeable beam,
  bomb mechanic, mid-boss every third wave, full boss every sixth.
- **Claudtra** — side-scrolling run-and-gun with checkpoint respawn and
  enemy variety.
- **Claude Fighter** — one-on-one brawler, four fighters with distinct
  power/speed/defense stats, AI that reactively blocks attack startups
  and punishes whiffs in recovery.
- **Super Claudio** — Mario-style platformer with coyote frames,
  variable-height jump, World 1-1 to the flagpole.
- **Claudturismo** — pseudo-3D top-down racing on a curving track,
  rivals with rubber-band speed scaling so races stay tight.
- **Claudemon** — creature-catching RPG with a FIRE/GRASS/WATER triangle,
  7 species + 1 uncatchable boss, ~6% crit chance on every move.
- **Final Claudesy** — full epic JRPG: three heroes (Knight, Mage, Healer),
  three regions, twenty-six spells, NewGame+ unlocked after the first
  victory.

Pick from the launcher with arrow keys, hit Enter, and the game fills
the terminal. Quit with ESC and you're back in the arcade in under a
second.

---

## The Design Brief

> Make it feel like a real arcade. Make it run anywhere with a TTY.
> Make installing it cost one command. Make every game look like its
> own thing instead of variations on a theme.

The constraints were the point. Python `curses` keeps the install free.
A single shared engine file keeps the source legible. Per-game ASCII
title art and palette choices keep the games from melting into one another.

---

## The Technical Lift

**A single engine file does the work of a game framework.** `claudcade_engine.py`
ships `Engine`, `Scene`, `Renderer`, `Input`, `Entity`, `PhysicsEntity`,
`AnimSprite`, `Camera`, `Particles`, plus rendering primitives (boxes,
bars, sprites, parallax stars, pause/gameover screens) — all in ~1,400
lines. Each game is one Python file that imports the engine, defines
its scenes, and chains `Engine().scene().run()`.

**Vibrant 256-color palette.** The engine binds the curses color pairs
to fixed cube indices (`#00ffff`, `#ff0000`, `#00ff00`, etc.) on
256-color terminals, falling back to named pairs on legacy ones.
Means the games render the same neon arcade colors in Ghostty,
iTerm2, Alacritty, and macOS Terminal — no theme dependency.

**Real global leaderboard.** Score submission is fire-and-forget over
HTTPS to a Netlify function fronting Neon Postgres. Each player is
auto-registered with a permanent ID on first run; the launcher shows
a "Welcome, Player #N" banner once and then just displays their ID in
the footer. Offline players get a local-only PB tracker that still
works without a network.

**MCP server with one-prompt install.** A custom Model Context Protocol
server exposes six tools to Claude Code: `setup`, `list_games`,
`leaderboard`, `submit_score`, `engine_docs`, and `scaffold`. The
`setup` tool emits the exact bash to install the arcade, write a
slash command, and launch it — Claude executes it without the user
typing a thing.

**Held-key input that actually feels like a console.** Terminal auto-repeat
is unreliable across emulators, so the engine maintains a 20-frame
grace window per keypress: tap a direction once and the player keeps
moving for 333ms, smoothing over the gap between initial-press and
auto-repeat onset. Tuned per-game so single taps feel responsive but
sustained input feels analog.

---

## The Collaboration Model

Built in pair-programming sessions with **Claude Code** as the
co-developer. Every game went through the same loop: design pitch →
prototype scene → tune the feel by running the game → iterate. The
games' AI logic (fighter's reactive blocking, racing rubber-band) was
designed in conversation, implemented in code, smoke-tested with
seeded RNG, and tuned by playtest — all in one session.

The repo's commit log reads as the running record of those sessions:
short, focused commits ("Game polish: crits, rubberbanding, reactive AI",
"Launcher: pre-register player + show Player ID + first-run welcome",
"Engine: vibrant 256-color palette + center the HOW TO PLAY screen").
Eight specialist agents ran a final cleanup audit — type consolidation,
unused code, defensive try/except review, circular imports, comment
quality — and surfaced a verified punch list before any code moved.

This case study is itself a co-author of the project: written in the
same terminal where the games run.

---

## What's On Disk

- **Repo:** [github.com/ConductorAILabs/claudecade](https://github.com/ConductorAILabs/claudecade)
- **Live site:** [claudecade.games](https://claudecade.games)
- **Standalone marquee:** [claudecade.games/marquee.html](https://claudecade.games/marquee.html)
- **Engine, as open-source dist:** `claudcade-engine/` (every game file
  is a symlink so the dist auto-syncs with the canonical source)

---

## Selected Quotes (for the highlight reel)

> "Seven games written in pure Python curses, scores backed by a real
> Postgres-powered global leaderboard."

> "The terminal arcade you launch from inside Claude Code."

> "Pure CSS + 9 lines of vanilla JS for the site — no third-party JS
> runs in production."

> "Pick a game with arrow keys, press Enter. ESC to quit back to your
> editor. That's the whole UX contract."

---

*Last updated: 2026-05-16.*
