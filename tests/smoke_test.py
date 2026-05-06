"""Headless smoke test — imports every shipped module to catch regressions.

Run with:  python3 -m tests.smoke_test
or:        python3 tests/smoke_test.py

Catches: syntax errors, missing imports, module-level side-effects.
Does NOT catch: runtime gameplay bugs (curses can't run headless).
"""
import importlib
import os
import sys
import traceback

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.insert(0, ROOT)

MODULES = [
    "claudcade_engine",
    "claudcade_scores",
    "claudcade_mcp",
    "claudcade",
    "ctype",
    "claudtra",
    "fight",
    "finalclaudesy.main",
    "finalclaudesy.battle",
    "finalclaudesy.entities",
    "finalclaudesy.explore",
    "finalclaudesy.data",
    "finalclaudesy.ui",
    "claudegames.server",
]


# Modules whose only failure mode is a missing optional dep — skipped if so.
OPTIONAL_DEPS = {"claudegames.server": "mcp"}


def main() -> int:
    failures: list[tuple[str, str]] = []
    skipped:  list[tuple[str, str]] = []
    for name in MODULES:
        try:
            importlib.import_module(name)
            print(f"  ok    {name}")
        except ModuleNotFoundError as e:
            optional = OPTIONAL_DEPS.get(name)
            if optional and optional == e.name:
                skipped.append((name, optional))
                print(f"  skip  {name}  (optional dep '{optional}' not installed)")
                continue
            failures.append((name, traceback.format_exc()))
            print(f"  FAIL  {name}")
        except Exception:
            failures.append((name, traceback.format_exc()))
            print(f"  FAIL  {name}")

    if failures:
        print(f"\n{len(failures)} module(s) failed to import:\n")
        for name, tb in failures:
            print(f"── {name} ──")
            print(tb)
        return 1
    print(f"\nAll {len(MODULES) - len(skipped)} required modules imported cleanly"
          f" ({len(skipped)} skipped).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
