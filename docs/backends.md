# orca-ext-utils — backend support matrix

Per-module, per-platform behavior. The library is honest about what
works; functions return sentinels (`None`, `False`, etc.) when a
backend can't service the call, rather than raising.

## Display-server detection

`_backend.is_x11()` and `_backend.is_wayland()` check the GDK
default display's class name (`X11Display` vs `WaylandDisplay`).
That's the most authoritative signal because it reflects what
GTK-using code (including XTest synth via AT-SPI) will actually
target.

Env-var fallbacks (`WAYLAND_DISPLAY`, `DISPLAY`) are only consulted
when Gdk can't be imported or returns no default display. They
DELIBERATELY don't trust `XDG_SESSION_TYPE` because that env var is
notoriously wrong on common Linux distributions (Fedora MATE on
X11 sets `XDG_SESSION_TYPE=wayland` but is really X11 — see
`~/.claude/projects/-home-codyhurst/memory/project_fedora_setup.md`
for the user's specific case).

## screen_rect

| Function | X11 (native) | X11 (GTK4 / XWayland) | Wayland (Mutter) | Wayland (KWin) | Wayland (wlroots) |
|---|---|---|---|---|---|
| `for_accessible(obj)` | works | works via fallback | returns `None` | returns `None` | returns `None` |
| `for_active_window()` | works | works | returns `None` | returns `None` | returns `None` |

The X11 fallback path covers the case where AT-SPI's
`get_extents(SCREEN)` returns `-1, -1` (a common failure for GTK4
apps that haven't populated the screen-coord bridge correctly).
It uses Gdk's `get_active_window()` + `get_origin()` to find the
toplevel's screen position, then offsets by the WINDOW-relative
extents AT-SPI does provide.

For Wayland: no library can return real screen coordinates
because the compositor doesn't expose them through any standard
API. The portal `RemoteDesktop` interface returns cursor position
but not arbitrary window rects. A future v0.3 may add best-effort
portal-based queries; today the answer is `None`.

## mouse_input

| Function | X11 | Wayland (Mutter) | Wayland (KWin) | Wayland (wlroots) |
|---|---|---|---|---|
| `click_at` | works | rarely | rarely | rarely |
| `double_click_at` | works | rarely | rarely | rarely |
| `press_at` / `release_at` | works | rarely | rarely | rarely |
| `move_to` | works | rarely | rarely | rarely |

"Rarely" on Wayland: AT-SPI's `generate_mouse_event` is
implemented by the compositor, and most compositors haven't
implemented the input-synth half of the AT-SPI interface. When
it isn't implemented, the call silently no-ops and we return
`True` anyway because there's no way to detect the no-op from
the Python side.

A future v0.2 will add explicit Wayland support via the portal
`RemoteDesktop` interface (which DOES work universally for input
synth, but requires a user-permission dialog and per-session
token management).

## keyboard_grab

| Function | X11 | Wayland (Mutter) | Wayland (KWin) | Wayland (wlroots) |
|---|---|---|---|---|
| `KeysetGrab.__enter__` | grabs registered | partial | partial | not honored |
| Callback delivery | works | works for registered | works for registered | no-op |
| `failed_keysyms` | populated on conflict | populated on rejection | populated on rejection | populated for all |

X11: `Atspi.Device.add_key_grab` is mutually exclusive across
clients. If another process already holds the grab for a given
`(keysym, modifier)` pair, the registration returns 0 and we
record the failure in `failed_keysyms`. Common cases that cause
this: GNOME Shell's global keybindings, KDE's KWin shortcuts.

Wayland: most compositors don't honor add_key_grab through the
AT-SPI bridge. `failed_keysyms` will contain the full requested
list. Extension authors should surface this to the user ("could
not capture some keys — check your compositor's accessibility
settings").

## window_info

| Function | X11 | Wayland |
|---|---|---|
| `active_window_rect` | works | returns `None` |
| `active_window_xid` | works | returns `None` |

`active_window_xid` is by definition X11-only because Wayland
windows don't have X11 window IDs. `active_window_rect` returns
`None` on Wayland because Gdk's `get_origin()` returns success=False
there (the compositor doesn't expose the toplevel's screen
position to non-privileged clients).

## screen_capture

| Function | X11 (Xorg) | XWayland | Wayland (Mutter) | Wayland (KWin) | Wayland (wlroots) |
|---|---|---|---|---|---|
| `capture_region_async` (Gdk) | works | works for XWayland apps | n/a | n/a | n/a |
| `capture_region_async` (ImageMagick) | works if `import` installed | works | n/a | n/a | n/a |
| `capture_region_async` (portal) | works | works | works | works | works (if `xdg-desktop-portal-wlr` installed) |
| `upscale_png` | works | works | works | works | works |

Backends are tried in order: Gdk → ImageMagick → portal. The first
two are synchronous; portal is async via D-Bus. On Wayland, only
the portal backend will succeed, and it MAY prompt the user the
first time a given process requests a screenshot (one-time per
session). Callers should treat first-time latency as several seconds.

## compositor_query

| Function | X11 | Wayland |
|---|---|---|
| `monitors()` | works | works |
| `primary_monitor()` | works | works (when compositor exposes one) |
| `monitor_at_point(x, y)` | works | works |
| `virtual_screen_rect()` | works | works |

All queries go through `Gdk.Display.get_monitor`, which is backed
by Xrandr on X11 and `xdg_output` on Wayland. Both work the same
from the API's perspective. Hot-plug events may cause a transient
`None` return during compositor reconfiguration; callers should
retry once if a fresh monitor list comes back empty.

## text_to_braille

| Function | Without liblouis | With liblouis |
|---|---|---|
| `text_to_cells(text)` | ASCII table only (US computer braille) | Same — table not auto-selected |
| `text_to_cells(text, table="en-ueb-g2.ctb")` | falls back to ASCII | UEB Grade 2 contractions |
| `text_to_cells(text, table="ko-g1.ctb")` | falls back to ASCII (blank for Korean) | Korean braille |
| `available_backends()` | `("ascii",)` | `("ascii", "liblouis")` |

liblouis is an optional dep. Install with `dnf install python3-louis`
or `apt install python3-louis` to enable contracted English and
non-Latin scripts. The ASCII table is always available and covers
a-z, 0-9, common punctuation in US computer (8-dot) braille.

## notification

| Function | All platforms |
|---|---|
| `notify(...)` | works iff a notification daemon is running (most desktops ship one) |
| `close(...)` | works on same conditions |
| `is_available()` | True iff `gi.repository.Notify` imports successfully |

Display server agnostic — uses the D-Bus
`org.freedesktop.Notifications` interface. Headless environments
(SSH, CI) get `is_available() == True` if libnotify is installed
but `notify()` is a no-op (no daemon to receive the call).

## process_supervisor

| Function | All platforms |
|---|---|
| `is_available(executable)` | works via shutil.which |
| `run_sync(argv, ...)` | works; blocks calling thread |
| `run_async(argv, on_done, ...)` | works; needs GLib main loop running |

Pure subprocess machinery — no display server interaction.

## key_combo_helpers

| Function | All platforms |
|---|---|
| `parse_chord("Ctrl+Shift+a")` | works (pure Python table) |
| `format_chord(mask, keysym)` | works |
| `name_to_keysym(name)` | works for built-in table; Gdk fallback when display is available |
| `keysym_to_name(keysym)` | works for built-in table; Gdk fallback when display is available |

The built-in table covers letters, digits, function keys, common
named keys, and the numeric keypad. The Gdk fallbacks extend
coverage to exotic keysyms but require a default display; in
headless environments they return 0 / None silently.

## extension_settings

| Function | GSettings schema installed | No schema |
|---|---|---|
| `get(key)` | reads GSettings | reads JSON file |
| `set(key, value)` | writes GSettings | atomic JSON write |
| `delete(key)` | GSettings reset | removes JSON key |
| `keys()` | GSettings list_keys | JSON dict keys |
| `backend()` | `"gsettings"` | `"json"` |

GSettings is preferred when an extension ships a schema
(`org.gnome.orca.extensions.<name>.gschema.xml` installed to
`/usr/share/glib-2.0/schemas/` or `$HOME/.local/share/glib-2.0/
schemas/`). The JSON fallback writes to
`$XDG_CONFIG_HOME/orca/extensions/<name>.json` with an atomic
write (temp + rename in the same directory).
