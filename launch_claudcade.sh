#!/bin/bash
# Launches the Claudcade arcade in a new tmux window using send-keys
# (running the command interactively in bash so curses can initialize properly).

LOG=/tmp/claudcade-launch.log
exec > >(tee -a "$LOG") 2>&1

echo "═══════════════════════════════════════════════════════════════"
echo "[CLAUDCADE LAUNCH] $(date '+%Y-%m-%d %H:%M:%S')"

# Verify game is installed
if [ ! -f "$HOME/claudecade/claudcade.py" ]; then
  echo "[ERROR] ~/claudecade/claudcade.py NOT FOUND. Install first."
  exit 2
fi

# Determine target tmux session
if [ -n "$TMUX" ]; then
  SESSION=$(tmux display-message -p '#S')
  echo "[INFO] In tmux: session '$SESSION'"
else
  # Try to find the attached client's session first
  SESSION=$(tmux list-clients -F '#{session_name}' 2>/dev/null | head -1)
  if [ -z "$SESSION" ]; then
    # Fallback: use the most recently active session
    SESSION=$(tmux list-sessions -F '#{session_activity} #{session_name}' 2>/dev/null \
      | sort -rn | head -1 | awk '{print $2}')
    if [ -z "$SESSION" ]; then
      echo "[ERROR] No tmux session found at all."
      echo "  Quit Claude (Ctrl+C), then run: tmux ; claude ; /claudecade"
      exit 3
    fi
    echo "[INFO] No attached client, using most recent session: '$SESSION'"
  else
    echo "[INFO] No \$TMUX, using attached session: '$SESSION'"
  fi
fi

# Step 1: create a fresh interactive bash window
echo "[ACTION] Creating new window in session $SESSION..."
tmux new-window -t "${SESSION}:" -n CLAUDCADE
RC=$?
if [ $RC -ne 0 ]; then
  echo "[ERROR] new-window failed (rc=$RC)"
  exit 4
fi

# Step 2: send keys to that window — bash will execute python interactively,
# so curses gets a proper TTY context. Trailing `; exit` closes the window
# when the game ends instead of dropping the user at a bash prompt in
# ~/claudecade (which is confusing — they think they "moved" directories).
echo "[ACTION] Sending launch command to new window..."
tmux send-keys -t "${SESSION}:CLAUDCADE" \
  "clear && cd ~/claudecade && python3 claudcade.py; exit" Enter

# Step 3: switch focus
tmux select-window -t "${SESSION}:CLAUDCADE"

echo "[OK] Arcade launching in tmux window '${SESSION}:CLAUDCADE'"
echo "═══════════════════════════════════════════════════════════════"
