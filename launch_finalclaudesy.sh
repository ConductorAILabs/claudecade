#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
GAME="python3 $DIR/finalclaudesy.py"
if [ -n "$TMUX" ]; then
    tmux split-window -v -p 45 "$GAME"
else
    tmux new-session "$GAME"
fi
