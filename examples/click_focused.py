#!/usr/bin/env python3
"""Example: click the center of whatever object currently has focus.

Demonstrates the full chain:
  1. Find the focused accessible via AT-SPI.
  2. Get its screen rect.
  3. Click the center.

Run inside an Orca extension context, or standalone with at-spi
available:

    python3 examples/click_focused.py

It will click whatever your pointer's focused accessible is. Be
careful where your focus is parked before running.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import gi  # noqa: E402

gi.require_version("Atspi", "2.0")
from gi.repository import Atspi  # noqa: E402

from orca_ext_utils import mouse_input, screen_rect  # noqa: E402


def main() -> int:
    desktop = Atspi.get_desktop(0)
    if desktop is None:
        print("error: no AT-SPI desktop available", file=sys.stderr)
        return 1

    # Walk the desktop to find the focused object. In a real
    # extension this would come from Orca's focus manager via the
    # controller; we walk here so the example is self-contained.
    focused = _find_focused(desktop)
    if focused is None:
        print("no focused accessible found", file=sys.stderr)
        return 1

    print(f"focused: {focused.get_name()!r} ({focused.get_role_name()})")

    rect = screen_rect.for_accessible(focused)
    if rect is None:
        print("screen_rect returned None -- Wayland session?", file=sys.stderr)
        return 1

    x, y, w, h = rect
    print(f"rect: x={x} y={y} w={w} h={h}")

    center_x, center_y = x + w // 2, y + h // 2
    if mouse_input.click_at(center_x, center_y):
        print(f"clicked ({center_x}, {center_y})")
        return 0
    print("click failed", file=sys.stderr)
    return 1


def _find_focused(obj: Atspi.Accessible) -> Atspi.Accessible | None:
    """Depth-first walk for an accessible with the FOCUSED state."""

    state_set = obj.get_state_set()
    if state_set is not None and state_set.contains(Atspi.StateType.FOCUSED):
        return obj

    for i in range(obj.get_child_count()):
        try:
            child = obj.get_child_at_index(i)
        except Exception:  # pylint: disable=broad-except
            continue
        if child is None:
            continue
        found = _find_focused(child)
        if found is not None:
            return found
    return None


if __name__ == "__main__":
    sys.exit(main())
