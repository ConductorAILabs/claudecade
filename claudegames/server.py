#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "claudegames",
    instructions=(
        "Launch ASCII terminal games in a tmux split pane alongside Claude Code. "
        "Run Claude Code inside tmux for the best experience: "
        "`tmux new-session -s claude` then `claude`."
    ),
)

# Games live one directory up from the package.
GAMES_DIR = Path(__file__).resolve().parent.parent


def _launch(game_file: str, title: str) -> str:
    path = GAMES_DIR / game_file
    if not path.exists():
        return f"Game file not found: {path}"

    cmd = f"python3 {path}"
    in_tmux = bool(os.environ.get("TMUX"))

    if in_tmux:
        result = subprocess.run(
            ["tmux", "split-window", "-v", "-p", "45", cmd],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            return f"{title} launched in split pane. Press ESC to quit back to Claude."
        return f"Failed to launch: {result.stderr.strip()}"

    return (
        f"Not running inside tmux — run Claude Code inside tmux for split-pane games:\n\n"
        f"  tmux new-session -s claude\n"
        f"  claude\n\n"
        f"Or play directly in a separate terminal:\n"
        f"  python3 {path}"
    )


@mcp.tool()
def launch_ctype() -> str:
    """Launch C-TYPE, a space shooter with enemy waves, power-ups, and a boss fight.
    Controls: W/A/S/D to move, J to shoot (hold for charge beam), ESC to quit."""
    return _launch("ctype.py", "C-TYPE")


@mcp.tool()
def launch_fight() -> str:
    """Launch Claude Fighter, a two-character ASCII fighting game.
    Controls: A/D to move, SPACE to jump, J/K/L to punch/kick/block, ESC to quit."""
    return _launch("fight.py", "Claude Fighter")


@mcp.tool()
def launch_claudtra() -> str:
    """Launch CLAUDTRA, a side-scrolling action platformer with enemies and bosses.
    Controls: A/D to move, SPACE to jump, J to shoot, ESC to quit."""
    return _launch("claudtra.py", "CLAUDTRA")


@mcp.tool()
def launch_finalclaudesy() -> str:
    """Launch FINAL CLAUDESY, a turn-based JRPG with towns, dungeons, and a final boss.
    Controls: WASD/arrows to navigate, SPACE/Enter to confirm, Q/ESC to cancel."""
    return _launch("finalclaudesy.py", "FINAL CLAUDESY")


@mcp.tool()
def launch_claudcade() -> str:
    """Launch the Claudcade arcade menu — pick a game from the launcher.
    Controls: Up/Down/W/S to select, Enter/Space to launch, Q to quit."""
    return _launch("claudcade.py", "Claudcade")


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
