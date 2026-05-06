"""
Hello World — the simplest possible Claudcade game.

A bouncing @ symbol. Run with: python3 hello_world.py
"""
from claudcade_engine import Engine, Scene, Renderer, Input, WHITE, CYAN, YELLOW


class BounceScene(Scene):
    def on_enter(self):
        self.x  = 10.0
        self.y  = 5.0
        self.vx = 0.5
        self.vy = 0.3

    def update(self, inp: Input, tick: int) -> str | None:
        H, W = self.engine.H, self.engine.W

        self.x += self.vx
        self.y += self.vy

        if self.x <= 1 or self.x >= W - 2:  self.vx *= -1
        if self.y <= 3 or self.y >= H - 3:  self.vy *= -1

        if inp.pause:
            return "quit"

    def draw(self, r: Renderer, tick: int):
        r.header("HELLO WORLD", right="ESC to quit", color=CYAN)
        r.outer_border()
        r.text(int(self.y), int(self.x), '@', YELLOW, bold=True)
        r.center(self.engine.H // 2, "Move the @ around", WHITE)


Engine("Hello World", fps=30).scene("main", BounceScene()).run("main")
