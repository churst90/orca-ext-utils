# orca-ext-utils

Shared utilities for [Orca](https://gitlab.gnome.org/GNOME/orca) user
extensions: things the upstream Orca controller deliberately won't
ship (per scope discipline: *"Orca shouldn't carry utilities it
doesn't need itself"*), but that multiple extensions actually need.

Designed to be either installed as a library OR **vendored** into
individual `.orca-ext` archives. NVDA add-ons have shipped utilities
this way for years; the pattern works well when the user shouldn't
need to know what pip is.

## Modules

Each module is independent -- vendor or import only the ones you need.

| Module | What it does |
|---|---|
| `screen_rect` | Screen-coord rect for an AT-SPI accessible object. |
| `screen_capture` | Region capture (Gdk → ImageMagick → xdg-desktop-portal). |
| `mouse_input` | Mouse click / press / release / move synthesis at coords. |
| `keyboard_grab` | Batch wrapper around `Atspi.Device.add_key_grab` for "grab a keyset." |
| `window_info` | Active toplevel window: screen rect + X11 window ID. |
| `compositor_query` | Multi-monitor geometry, DPI scaling, refresh rate. |
| `text_to_braille` | Text → braille cell bytes (liblouis optional, ASCII fallback). |
| `notification` | libnotify desktop-notification facade with consistent app-name. |
| `process_supervisor` | Sync + async subprocess with timeout, signals, GLib integration. |
| `key_combo_helpers` | keysym ↔ name, modifier-mask parsing, chord serialization. |
| `extension_settings` | Per-extension key/value store (GSettings or JSON fallback). |
| `_backend` | X11 vs Wayland detection (Gdk display class + env fallback). |

See [docs/backends.md](docs/backends.md) for the per-feature
support matrix on X11 vs Wayland.

## Install

### As a library (development / quick prototype)

```sh
pip install --user -e .
```

Then in your extension:

```python
from orca_ext_utils import screen_rect, mouse_input

rect = screen_rect.for_accessible(some_atspi_object)
if rect is not None:
    x, y, w, h = rect
    mouse_input.click_at(x + w // 2, y + h // 2)
```

### Vendored into a .orca-ext archive (recommended for shipping)

Copy the `orca_ext_utils/` package into your extension's source
tree under a `vendor/` directory, then import via relative path:

```python
from .vendor.orca_ext_utils import screen_rect
```

See [docs/vendoring.md](docs/vendoring.md) for the full workflow
and a `vendor/UPDATE.md` template that records which version you
synced from.

## Why bundled / vendored over PyPI

For the Orca user base specifically, asking end users to manage
Python dependencies is hostile. The `.orca-ext` archive format is
designed around "one file, one install, done." Vendoring respects
that. NVDA add-ons solved the same problem the same way.

The trade-off is code duplication across extensions when two of
them vendor the same utility. The win is **failure isolation**
(a bug in screen-rect for one extension doesn't break another)
and **zero dependency management** for the user. Both wins
outweigh the duplication for a small ecosystem.

If you want a centralized version anyway, install from this repo
and treat it as you would any Python library. Both shapes work.

## What this library does NOT cover

- **Wayland screen coordinates.** No userspace library can
  manufacture coords the compositor doesn't expose through
  standard accessibility APIs. The functions return `None` under
  Wayland; document the limitation in your extension's UI. The
  real fix is a multi-year project upstream of every component
  involved (at-spi2-core, GTK4, Mutter/KWin).
- **Clipboard get/set.** Orca's controller will ship this directly
  via `controller.get_clipboard_text` / `set_clipboard_text` using
  the gpaste / klipper / GtkClipboard chain. Use that.
- **Speech / braille synthesis taps.** Use the controller's
  `subscribe_speech_emitted` / `subscribe_braille_emitted` /
  `subscribe_keyboard_event` hooks directly.
- **D-Bus notifications.** Use `dasbus` or `Gio.DBusProxy`
  directly; we don't add a wrapper.

## Backend coverage at a glance

| Module | X11 | Wayland | Notes |
|---|---|---|---|
| `screen_rect.for_accessible` | full | returns `None` | Atspi + Gdk.X11 fallback. |
| `screen_rect.for_active_window` | full | returns `None` | Gdk-based. |
| `screen_capture.capture_region_async` | full (Gdk / ImageMagick) | full (xdg-portal) | Async on Wayland; portal may prompt user on first call per session. |
| `screen_capture.upscale_png` | works | works | Pure GdkPixbuf, no display server needed. |
| `mouse_input.click_at` | works | compositor-dependent | XTest under AT-SPI on X11; Wayland varies. |
| `mouse_input.move_to` | works | compositor-dependent | Same. |
| `keyboard_grab.KeysetGrab` | works | compositor-dependent | `failed_keysyms` reports which grabs the system refused. |
| `window_info.active_window_rect` | works | returns `None` | Gdk's `get_origin` returns "unknown" on Wayland. |
| `window_info.active_window_xid` | works | returns `None` | XID is X11-only by definition. |
| `compositor_query.monitors` | works | works | Both via `Gdk.Display.get_monitor`. |
| `compositor_query.monitor_at_point` | works | works | Same. |
| `text_to_braille.text_to_cells` | works | works | Pure-Python; liblouis optional for non-Latin / Grade 2. |
| `notification.notify` | works | works | Backed by libnotify (org.freedesktop.Notifications). |
| `process_supervisor.run_sync` | works | works | Pure subprocess; no display server needed. |
| `process_supervisor.run_async` | works | works | Needs a running GLib main loop. |
| `key_combo_helpers.parse_chord` | works | works | Pure Python table + optional Gdk fallback. |
| `extension_settings.Settings` | works | works | GSettings if schema installed, JSON file under `$XDG_CONFIG_HOME/orca/extensions/` otherwise. |

## Tests

```sh
python3 -m pytest tests/
```

Mock-heavy unit tests; the production code talks to a live display.
Integration tests against a real X server are tracked in `tests/integration/` (not present in v0.1).

## License

LGPL-2.1-or-later, matching Orca. See `LICENSE`.
