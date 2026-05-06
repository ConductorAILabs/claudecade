"""Run each game in a real PTY for ~1.5s and look for stack traces.

Catches: curses init bugs, missing imports under real-tty conditions, immediate
crashes that wouldn't show in a plain `import` smoke test.

This test is best-effort — curses output is binary noise, so we just look for
'Traceback' in the output. Press Q sequence is sent to ask the games to exit
gracefully when possible.
"""
import os
import pty
import select
import signal
import subprocess
import sys
import time

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

GAMES = [
    ("claudcade.py",      [b"q"]),
    ("ctype.py",          [b"\x1b", b"q"]),     # ESC, then q
    ("claudtra.py",       [b"\x1b", b"q"]),
    ("fight.py",          [b"\x1b", b"q"]),
    ("finalclaudesy.py",  [b"q", b"\x1b"]),
]


def run_game(rel_path: str, exit_keys: list[bytes]) -> tuple[bool, str]:
    """Launch the game in a PTY, send exit keys, kill after timeout. Return (ok, output)."""
    path = os.path.join(ROOT, rel_path)
    pid, fd = pty.fork()
    if pid == 0:  # child
        os.environ["TERM"] = "xterm-256color"
        os.execvp(sys.executable, [sys.executable, path])

    output = bytearray()
    deadline = time.monotonic() + 2.5
    sent_exit = False
    try:
        while time.monotonic() < deadline:
            ready, _, _ = select.select([fd], [], [], 0.1)
            if ready:
                try:
                    chunk = os.read(fd, 4096)
                except OSError:
                    break
                if not chunk:
                    break
                output.extend(chunk)
            # Send exit keys after ~1s once the game is up
            if not sent_exit and time.monotonic() > deadline - 1.5:
                for k in exit_keys:
                    try: os.write(fd, k)
                    except OSError: pass
                    time.sleep(0.15)
                sent_exit = True
            # Check if child exited
            try:
                done_pid, _ = os.waitpid(pid, os.WNOHANG)
                if done_pid != 0:
                    break
            except ChildProcessError:
                break
    finally:
        try: os.kill(pid, signal.SIGTERM)
        except ProcessLookupError: pass
        try: os.waitpid(pid, 0)
        except ChildProcessError: pass
        try: os.close(fd)
        except OSError: pass

    text = output.decode("utf-8", errors="replace")
    has_traceback = "Traceback" in text or "crashed]" in text
    return (not has_traceback, text)


def main() -> int:
    failures = []
    for rel, keys in GAMES:
        ok, text = run_game(rel, keys)
        status = "ok  " if ok else "FAIL"
        print(f"  {status}  {rel}")
        if not ok:
            failures.append((rel, text))

    if failures:
        print(f"\n{len(failures)} game(s) crashed:\n")
        for rel, text in failures:
            print(f"── {rel} ──")
            # Strip ANSI escape sequences for readability
            import re
            cleaned = re.sub(r"\x1b\[[\d;?]*[A-Za-z]", "", text)
            cleaned = re.sub(r"\x1b\][\d;]*[\x07\x1b\\]", "", cleaned)
            cleaned = re.sub(r"\x1b[()][AB012]", "", cleaned)
            cleaned = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", cleaned)
            print(cleaned[-2000:])
        return 1
    print(f"\nAll {len(GAMES)} games launched cleanly in PTY.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
