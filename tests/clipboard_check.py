#!/usr/bin/env python3
"""Check that andy's clipboard actually reaches the clipboard.

Not named test_*.py on purpose: it needs a display server, so the ordinary
suite must not pick it up. CI runs it under Xvfb and under headless sway; see
the `clipboard` job in .github/workflows/test.yml.

    python3 tests/clipboard_check.py wayland     # reads back with wl-paste
    python3 tests/clipboard_check.py x11         # reads back with xclip
    python3 tests/clipboard_check.py x11-xsel    # reads back with xsel
    python3 tests/clipboard_check.py none        # expects an honest failure
"""

import subprocess
import sys

from andymod import andy

READERS = {
    "wayland": ["wl-paste", "-n"],
    "x11": ["xclip", "-selection", "clipboard", "-o"],
    "x11-xsel": ["xsel", "--clipboard", "--output"],
}

# The two things andy actually puts on the clipboard.
SAMPLES = (
    ("a reclaim command", "cargo clean   # run inside the project"),
    ("a path with spaces", "/home/dev/Library/Application Support/Code/Cache"),
)


def main(mode: str) -> int:
    print(f"mode {mode}; andy tries {[c[0] for c in andy.CLIPBOARDS]}")

    if mode == "none":
        # nothing installed: a clear False, not an exception and not a lie
        if andy.clip("anything") is not False:
            print("FAIL: clip() claimed success with no clipboard tool")
            return 1
        print("  ok: clip() returned False")
        return 0

    reader = READERS[mode]
    for label, text in SAMPLES:
        if not andy.clip(text):
            print(f"FAIL: clip() returned False for {label}")
            return 1
        back = subprocess.run(reader, capture_output=True, text=True, timeout=20)
        if back.stdout.strip() != text:
            print(f"FAIL: {label}\n  put {text!r}\n  got {back.stdout!r} {back.stderr!r}")
            return 1
        print(f"  ok: {label}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else "none"))
