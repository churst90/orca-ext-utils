#!/usr/bin/env python3
"""Example: grab letter keys a-z under all modifiers and log them.

Demonstrates the keyboard_grab.KeysetGrab context manager.
Run standalone:

    python3 examples/grab_keyset.py

Press any letter to see it logged. Ctrl+C to exit. Other keys
(arrows, F-keys, etc.) pass through normally.

This is the same primitive orca-remote uses for full system-level
master-side key capture (once the corresponding feature lands).
"""

from __future__ import annotations

import signal
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import gi  # noqa: E402

gi.require_version("Atspi", "2.0")
from gi.repository import Atspi, GLib  # noqa: E402

from orca_ext_utils.keyboard_grab import KeysetGrab  # noqa: E402


def main() -> int:
    # XK_a through XK_z.
    keysyms = list(range(0x61, 0x7b))

    def on_key(event: Atspi.DeviceEvent) -> bool:
        kind = "press" if event.type == Atspi.EventType.KEY_PRESSED_EVENT else "release"
        print(
            f"[grabbed] keysym=0x{event.id:x} modifiers=0x{event.modifiers:x} "
            f"text={event.event_string!r} ({kind})"
        )
        # Return False = pass-through; the focused app still sees
        # the key. Return True to consume.
        return False

    with KeysetGrab(keysyms) as grab:
        print(
            f"grabbed {len(grab._grab_ids)} key combinations "
            f"({len(grab.failed_keysyms)} failed)"
        )
        if grab.failed_keysyms:
            print(
                "  failed (likely already grabbed by another app):",
                grab.failed_keysyms[:5],
                "..." if len(grab.failed_keysyms) > 5 else "",
            )
        ok = grab.register(on_key)
        if not ok:
            print("error: could not register key callback", file=sys.stderr)
            return 1

        print("Press letter keys (Ctrl+C to exit)...")

        loop = GLib.MainLoop()
        signal.signal(signal.SIGINT, lambda *_: loop.quit())
        loop.run()

    print("released all grabs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
