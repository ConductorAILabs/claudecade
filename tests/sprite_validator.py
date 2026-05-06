"""Sprite alignment validator.

Walks list-of-string literals that look like sprite frames in the shipped game
files and verifies each frame's rows are uniform width. Catches the offset bugs
that show up when a sprite "leans" because one row has a stray space.

Heuristic: a sprite frame is a list literal whose elements are all string
literals of length >= 3, where at least 2 elements share the same length.

Run with: python3 tests/sprite_validator.py

This is a static analysis (no eval) — it only inspects syntax, so dynamic
sprite generation (e.g. frm() helpers in claudtra/fight) is not validated;
those generate fixed-width frames by construction.
"""
import ast
import os
import sys
from typing import Iterator

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))

# Files to validate. Skip incubator games and the engine itself (no sprites there).
TARGETS = [
    "ctype.py",
    "claudtra.py",
    "fight.py",
    "claudcade.py",
    "finalclaudesy/main.py",
]


def iter_string_lists(tree: ast.AST) -> Iterator[ast.List]:
    """Yield list literals whose elements are all string constants."""
    for node in ast.walk(tree):
        if not isinstance(node, ast.List):
            continue
        if not node.elts:
            continue
        if not all(isinstance(el, ast.Constant) and isinstance(el.value, str) for el in node.elts):
            continue
        yield node


def looks_like_sprite_frame(node: ast.List) -> bool:
    """Heuristic: list of >=2 strings that contain drawing chars (box/block/etc).

    Rejects plain text lists (controls, tips, story lines) that happen to look
    like sprite frames structurally.
    """
    rows = [el.value for el in node.elts if isinstance(el, ast.Constant)]
    if len(rows) < 2:
        return False
    if max(len(r) for r in rows) < 3:
        return False
    drawing = set("╔╗╚╝═║╠╣╦╩╬┌┐└┘─│├┤┬┴┼█▓▒░▀▄◢◣◤◥▌▐╱╲╫╪╭╮╰╯◀▶◁▷◄►◆◇◈◉")
    has_drawing = any(any(c in drawing for c in r) for r in rows)
    if not has_drawing:
        return False
    lens = [len(r) for r in rows]
    return max(lens) - min(lens) <= 6


def validate_frame(rows: list[str]) -> tuple[bool, str]:
    """A frame is uniform if all rows have the same length."""
    lens = {len(r) for r in rows}
    if len(lens) == 1:
        return True, ""
    target = max(lens)
    bad = [(i, len(r)) for i, r in enumerate(rows) if len(r) != target]
    return False, f"row widths differ — expected {target}, off rows: {bad}"


def validate_file(path: str) -> list[str]:
    """Return list of issue strings for a file."""
    issues: list[str] = []
    with open(path) as f:
        src = f.read()
    try:
        tree = ast.parse(src, path)
    except SyntaxError as exc:
        return [f"{path}: parse error {exc}"]
    for node in iter_string_lists(tree):
        if not looks_like_sprite_frame(node):
            continue
        rows = [el.value for el in node.elts if isinstance(el, ast.Constant)]
        ok, detail = validate_frame(rows)
        if not ok:
            issues.append(f"{path}:{node.lineno}: {detail}")
    return issues


def main() -> int:
    all_issues: list[str] = []
    for rel in TARGETS:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            print(f"  skip  {rel}  (not found)")
            continue
        issues = validate_file(path)
        if issues:
            all_issues.extend(issues)
            print(f"  FAIL  {rel}  ({len(issues)} issue(s))")
        else:
            print(f"  ok    {rel}")

    if all_issues:
        print(f"\n{len(all_issues)} sprite alignment issue(s):")
        for issue in all_issues:
            print(f"  {issue}")
        return 1
    print("\nAll sprite frames have uniform row widths.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
