# Claudcade Engine

A minimal terminal game engine for Python. No dependencies. Any terminal. macOS, Linux, WSL.

Build a complete terminal game in under 100 lines. When you ship something cool, tag us — we'll share it.

**[@claudcade](https://starlit-macaron-113a83.netlify.app)**

---

```
  ___  _      _   _   _  ___   ___   _    ___  ___
 / __|| |    /_\ | | | ||   \ / __| /_\  |   \| __|
| (__ | |__ / _ \| |_| || |) | (__ / _ \ | |) | _|
 \___||____/_/ \_\\___/ |___/ \___/_/ \_\|___/|___|
```

---

## Requirements

- Python 3.10+
- tmux (recommended — games open in a split pane)
- Any terminal, 80×24 minimum
- No pip install. No dependencies.

Install tmux if you don't have it:
```bash
# macOS
brew install tmux

# Ubuntu / Debian
sudo apt install tmux
```

---

## Play the games

```bash
git clone https://github.com/ConductorAILabs/claudecade.git
cd claudecade

# Start a tmux session first (recommended)
tmux

# Then launch the arcade
python3 claudcade.py
```

Select a game with arrow keys, press Enter. If you're inside tmux the game opens in a split pane below. If you're not in tmux it opens directly in your terminal — both work fine.

---

## Build your own game

Copy `claudcade_engine.py` next to your game file. That's the entire install.

```python
from claudcade_engine import Engine, Scene, Renderer, Input, CYAN, YELLOW

class GameScene(Scene):
    def on_enter(self):
        self.x, self.y = 10.0, 5.0

    def update(self, inp: Input, tick: int) -> str | None:
        if inp.left:  self.x -= 1
        if inp.right: self.x += 1
        if inp.up:    self.y -= 1
        if inp.down:  self.y += 1
        if inp.pause: return "quit"

    def draw(self, r: Renderer, tick: int):
        r.header("MY GAME", left="♥ ♥ ♥", right="SCORE: 000", color=CYAN)
        r.outer_border()
        r.text(int(self.y), int(self.x), '@', YELLOW, bold=True)

Engine("My Game", fps=30).scene("game", GameScene()).run("game")
```

Run it:

```bash
python3 my_game.py
```

---

## Core Concepts

### Engine

The engine manages the FPS-locked game loop, curses setup, and scene switching.

```python
engine = (
    Engine("My Game", fps=30)
    .scene("menu",     MenuScene())
    .scene("game",     GameScene())
    .scene("gameover", GameOverScene())
)
engine.run("menu")
```

| Method | Description |
|--------|-------------|
| `.scene(name, scene)` | Register a scene. Chainable. |
| `.run(initial_scene)` | Start the game loop. Blocks until quit. |
| `.switch(name)` | Switch to a scene immediately. |
| `engine.H`, `engine.W` | Terminal height and width (current frame). |

---

### Scene

A scene is one screen of your game — intro, gameplay, pause, game over, etc.

```python
class MyScene(Scene):
    def on_enter(self):
        # Called once when this scene becomes active.
        self.score = 0

    def update(self, inp: Input, tick: int) -> str | None:
        # Game logic. Return a scene name to switch, or None to stay.
        if inp.pause:
            return "pause"
        return None

    def draw(self, r: Renderer, tick: int):
        # Draw everything. Called every frame after update().
        r.header("MY GAME")
        r.center(self.engine.H // 2, f"Score: {self.score}")
```

Access the engine from any scene via `self.engine`.

---

### Input

One `Input` object is passed to `update()` each frame. It reflects the keys pressed during that frame.

```python
def update(self, inp: Input, tick: int) -> str | None:
    if inp.up:      self.y -= 1      # W or ↑
    if inp.down:    self.y += 1      # S or ↓
    if inp.left:    self.x -= 1      # A or ←
    if inp.right:   self.x += 1      # D or →
    if inp.fire:    self.shoot()     # J, F, or mouse click
    if inp.jump:    self.jump()      # SPACE
    if inp.confirm: return "next"   # ENTER or SPACE
    if inp.pause:   return "pause"  # ESC

    # Check any key directly:
    if inp.pressed(ord('r'), ord('R')):
        self.restart()
```

| Property | Keys |
|----------|------|
| `inp.up` | W, ↑ |
| `inp.down` | S, ↓ |
| `inp.left` | A, ← |
| `inp.right` | D, → |
| `inp.fire` | J, F, mouse click |
| `inp.jump` | SPACE |
| `inp.confirm` | ENTER, SPACE |
| `inp.pause` | ESC |
| `inp.pressed(key)` | any `ord()` key code |
| `inp.just_pressed(key)` | true only on the first frame the key went down |
| `inp.just_released(key)` | true only on the first frame the key came back up |
| `inp.mouse_click` | left mouse button |

**Held-key handling.** Terminal auto-repeat in most emulators (macOS Terminal, iTerm, gnome-terminal) waits ~500ms before sending the first key repeat. The engine maintains a 20-frame (~333ms @ 60 FPS) "still held" grace window on every key it sees, so `inp.pressed()` returns `True` continuously while a key is physically held even during the auto-repeat gap. You can do `if inp.left: self.x -= 1` and it Just Works.

---

### Renderer

The renderer is passed to `draw()` each frame. All operations are bounds-safe — drawing outside the terminal does nothing.

#### Text

```python
r.text(row, col, "Hello!", color=CYAN, bold=True)
r.center(row, "Centered text", color=YELLOW)
```

#### Layout

```python
r.outer_border()                            # full-screen ╔═╗╚═╝ border
r.header("GAME NAME", left="♥♥♥", right="SCORE: 100")
r.footer("WASD: Move   J: Shoot   ESC: Pause")
r.box(row, col, height, width, color=WHITE, title="Inventory")
```

#### Game elements

```python
r.bar(row, col, hp, max_hp, width=20, fill_color=GREEN)   # HP bar
r.sprite(row, col, [' /O\\ ', '/|=|\\', '/ \\/ \\'], color=CYAN)
r.stars(self.stars)                          # parallax star field
r.menu(row, col, ["New Game", "Quit"], cursor=0)
```

#### Built-in screens

```python
# Pause overlay (drawn over the current game scene). Minimal panel:
# "<game> · PAUSED" plus a [ R ] Resume / [ Q ] Quit prompt, no scrim,
# no controls table. The `controls` argument is accepted for API compat
# but no longer rendered — show your control map in the how-to-play
# scene or the gameover screen if you want it elsewhere.
r.pause_overlay("MY GAME", controls=[])

# Game over screen
r.gameover_screen(
    title="GAME  OVER",
    score_line=f"SCORE: {self.score:07d}   WAVE {self.wave}",
    player_label="Player #1",
    rank=3,
    tick=tick,
    prompt="[ SPACE ] Play again   [ ESC ] Quit",
)
```

#### Color constants

```python
CYAN      # player, info
RED       # enemies, danger
GREEN     # HP, nature, positive
YELLOW    # gold, fire, titles
WHITE     # borders, neutral text
MAGENTA   # magic, special
HIGHLIGHT # black on white — selected menu items
BLUE      # water, MP
```

---

### Entity

Base class for anything that moves.

```python
class Bullet(Entity):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.vx = 8.0

    def rect(self):
        return (self.x, self.y, 2.0, 1.0)   # for collision

    def update(self, inp, tick):
        self.x += self.vx
        if self.x > 200:
            self.alive = False

    def draw(self, r: Renderer):
        r.text(int(self.y), int(self.x), '=>', YELLOW, bold=True)

# Collision check
if bullet.collides(enemy):
    enemy.alive = False
```

### PhysicsEntity

Entity with gravity and floor collision built in.

```python
class Player(PhysicsEntity):
    gravity = 1.5

    def update(self, inp, tick):
        if inp.left:  self.vx = -2
        if inp.right: self.vx =  2
        if inp.jump and self.grounded:
            self.vy = -9

        self.apply_physics(floor_y=20)   # resolves gravity + floor
```

---

### AnimSprite

Frame-cycling sprite with named states.

```python
sprite = AnimSprite({
    'idle': [ [' O ', '/|\\', '/ \\'] ],
    'run':  [ [' O ', '/|>', '/ \\'], [' O ', '<|\\', '/ \\'] ],
    'hurt': [ ['>O<', '/|\\', '/ \\'] ],
}, ticks_per_frame=6)

# In update():
if moving: sprite.set_state('run')
else:      sprite.set_state('idle')
sprite.tick()

# In draw():
r.sprite(row, col, sprite.current(), color=CYAN)
```

---

### Camera

Smooth-follow camera for scrolling worlds.

```python
cam = Camera()

# In update():
cam.follow(player.x, player.y, lerp=0.08)

# In draw() — convert world coords to screen:
row, col = cam.world_to_screen(entity.x, entity.y, W, H)
r.sprite(row, col, entity.sprite)
```

---

### Particles

Explosions and sparks.

```python
fx = Particles()

# Trigger:
fx.explode(col, row)

# Each frame:
fx.update()
fx.draw(r)
```

---

### Utilities

```python
stars = make_stars(H, W, count=80)   # generate parallax stars
scroll_stars(stars, W)               # animate them (call each frame)

distance(ax, ay, bx, by)            # Euclidean distance
clamp(value, lo, hi)                 # clamp a number
lerp(a, b, t)                        # linear interpolation
```

---

## Patterns

### Pause menu

```python
CONTROLS = ["WASD  Move", "J     Shoot", "ESC   Pause"]

class GameScene(Scene):
    def update(self, inp, tick):
        if inp.pause:
            return "pause"

class PauseScene(Scene):
    def update(self, inp, tick):
        if inp.pressed(ord('r'), ord('R')) or inp.pause:
            return "game"
        if inp.pressed(ord('q'), ord('Q')):
            return "quit"

    def draw(self, r, tick):
        self.engine._scenes["game"].draw(r, tick)   # game behind overlay
        r.pause_overlay("MY GAME", CONTROLS)
```

### Multiple scenes

```python
class IntroScene(Scene):
    def update(self, inp, tick):
        if inp.confirm: return "game"
    def draw(self, r, tick):
        r.center(r.H // 2, "Press SPACE to start", YELLOW)

class GameOverScene(Scene):
    def update(self, inp, tick):
        if inp.confirm: return "game"
        if inp.pause:   return "quit"
    def draw(self, r, tick):
        r.gameover_screen(score_line=f"SCORE: {self.score}", tick=tick)

Engine("My Game").scene("intro", IntroScene()).scene("game", GameScene()) \
                 .scene("gameover", GameOverScene()).run("intro")
```

### Scrolling world

```python
class WorldScene(Scene):
    def on_enter(self):
        self.stars  = make_stars(24, 80)
        self.cam    = Camera()
        self.player = Player(10, 5)

    def update(self, inp, tick):
        self.player.update(inp, tick)
        self.cam.follow(self.player.x, self.player.y)
        scroll_stars(self.stars, self.engine.W)

    def draw(self, r, tick):
        r.header("MY GAME")
        r.stars(self.stars)
        row, col = self.cam.world_to_screen(
            self.player.x, self.player.y, self.engine.W, self.engine.H
        )
        r.sprite(row, col, self.player.sprite, CYAN)
```

---

## Full example

See `examples/hello_world.py` — a complete bouncing game in 28 lines.

More examples coming. If you build something, open a PR and add it to `examples/`.

---

## Built with this engine

| Game | Developer | Genre |
|------|-----------|-------|
| C-TYPE | Claudcade | Space shooter |
| Claudtra | Claudcade | Run & gun platformer |
| Claude Fighter | Claudcade | 1v1 fighting |
| Super Claudio | Claudcade | Side-scrolling platformer |
| Claudturismo | Claudcade | Top-down racing |
| Claudemon | Claudcade | Turn-based creature RPG |
| Final Claudesy | Claudcade | Epic JRPG |

Every game in this list is a single-file Python source you can crack
open right next to the engine in this repo — useful as a reference
when you're building your own.

Built something? Tag **@claudcade** — we share everything.

---

## AI agent usage (Claude Code)

This engine is designed to be LLM-friendly. If you're using Claude Code:

1. Add `claudcade_engine.py` to your project
2. Ask Claude to build a game using it
3. Claude can read this README through the MCP and scaffold a complete game

The class hierarchy is intentionally flat and named to be obvious to language models:
- `Engine` runs the loop
- `Scene` is one screen
- `Entity` is one thing in the world
- `Renderer` draws it

---

## License

MIT. Use it for anything. No attribution required (but we appreciate the tag).
