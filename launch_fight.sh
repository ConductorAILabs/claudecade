#!/bin/bash
# Launches the ASCII fighting game in a tmux split pane.
# If not in tmux, wraps Claude Code in tmux first.

DIR="$(cd "$(dirname "$0")" && pwd)"
GAME="python3 $DIR/fight.py"

if [ -n "$TMUX" ]; then
  # Already in tmux — split current window, game in bottom 45%
  tmux split-window -v -p 45 "$GAME"
else
  # Not in tmux yet — start a tmux session with the game in a split,
  # then re-attach Claude Code in the top pane.
  echo ""
  echo "  ┌─────────────────────────────────────────┐"
  echo "  │  To play games inside this window,      │"
  echo "  │  run Claude Code inside tmux:            │"
  echo "  │                                         │"
  echo "  │    tmux new-session -s claude            │"
  echo "  │    claude  (start Claude Code)           │"
  echo "  │                                         │"
  echo "  │  Then /fight will split the window.     │"
  echo "  │                                         │"
  echo "  │  One-time setup. Works forever after.   │"
  echo "  └─────────────────────────────────────────┘"
  echo ""
  echo "  Starting game in a new tmux session for now..."
  echo "  (ESC to exit game, then 'exit' to close tmux)"
  echo ""
  sleep 1
  tmux new-session "$GAME"
fi
