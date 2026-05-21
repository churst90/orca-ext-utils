"""orca-ext-utils -- shared utilities for Orca user extensions.

A small library covering capabilities the upstream Orca controller
deliberately won't ship (per scope discipline: "Orca shouldn't carry
utilities it doesn't need itself"). Extensions that need them can
either install this as a package or vendor the relevant modules
into their own `.orca-ext` archive.

Modules:

  screen_rect    -- screen-coordinate rect for an AT-SPI accessible.
  mouse_input    -- mouse click synthesis at screen coords.
  keyboard_grab  -- batch wrapper around Atspi.Device.add_key_grab.
  window_info    -- the currently-focused toplevel window.
  _backend       -- X11 vs Wayland session detection.

Per-backend coverage:

  X11:     all modules work via AT-SPI / XTest / Gdk.X11 paths.
  Wayland: screen_rect and window_info return None (no library
           can manufacture coords the compositor doesn't expose).
           mouse_input + keyboard_grab partially work via the AT-SPI
           paths the compositor does support; varies per compositor.

See docs/backends.md for the per-feature support matrix.
"""

from __future__ import annotations

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "screen_rect",
    "mouse_input",
    "keyboard_grab",
    "window_info",
]
