# orca-ext-utils — architecture

This file explains how the library is structured and why specific
decisions were made. For per-platform support details see
[backends.md](backends.md); for the vendoring workflow see
[vendoring.md](vendoring.md).

## Design principles

**1. No third-party Python dependencies.** The library uses only
the stdlib and PyGObject (`gi.repository.Atspi` / `Gdk` / `GLib`).
PyGObject isn't even listed in `pyproject.toml` because any system
running Orca already has it -- listing it would force pip to try
rebuilding against the typelib in ways that frequently fail.

**2. Never raise from a public function.** Every public function
returns either a useful result or a sentinel (`None`, `False`,
empty list) on any failure path. AT-SPI is full of edge cases
(no display attached, accessibility bus down, GTK4 quirks, Wayland
limits); we swallow exceptions and report failure via return value
so calling code can degrade gracefully.

**3. Backend-detect lazily.** `_backend.is_x11()` / `is_wayland()`
both `lru_cache(maxsize=1)` -- session type doesn't change for the
lifetime of a process, so we don't pay the Gdk import + class
check more than once. Cleared in tests via `cache_clear()`.

**4. Defer Wayland support honestly.** Many functions return `None`
on Wayland. We don't pretend that wrapping
`xdg-desktop-portal RemoteDesktop` is the same thing as having
working coordinates. Per-feature coverage is documented in
[backends.md](backends.md) so extension authors can decide whether
to refuse / degrade / warn.

## Module dependency graph

```
            ┌──────────────────────┐
            │    _backend          │   (X11/Wayland detection)
            └──────────┬───────────┘
                       │
            ┌──────────▼───────────┐
            │    window_info       │   (active toplevel rect / XID)
            └──────────┬───────────┘
                       │
            ┌──────────▼───────────┐
            │    screen_rect       │   (AT-SPI extents + Gdk fallback)
            └──────────────────────┘

            ┌──────────────────────┐
            │    mouse_input       │   (independent of above)
            └──────────────────────┘

            ┌──────────────────────┐
            │    keyboard_grab     │   (independent of above)
            └──────────────────────┘
```

`screen_rect.for_accessible` depends on `window_info.active_window_rect`
for the X11 fallback when AT-SPI returns invalid extents.
`mouse_input` and `keyboard_grab` are independent leaves.

## Why this library exists (the upstream story)

The orca-remote and orca-ocr extensions both need things the Orca
maintainer (Joanmarie Diggs) decided not to add to core Orca:

- **Screen-coord rect for accessible objects.** Used by OCR to know
  where to render/click on recognized text. Joanie's stance: Orca
  doesn't need this internally, and the Wayland coverage story is
  permanently messy, so she won't carry it.
- **XTest mouse synthesis fallback for X11.** AT-SPI's mouse synth
  works on X11 but Joanie won't carry XTest-direct fallback for
  the cases where the AT-SPI path is buggy. Same logic.
- **Per-keysym batch grabs.** orca-remote needs to grab a wide
  keyset when forwarding keys to a remote master. Joanie hasn't
  taken a position on this yet but the use case is extension-side
  not Orca-side.
- **Active window detection.** Joanie has agreed in principle to a
  controller method returning the focused-toplevel AT-SPI object,
  but the screen-coord rect of that window stays out of Orca.

The library is the agreed-on answer to "where does this code live."
See `~/email-joanie-api-surfaces.md` and the reply in
`~/email-joanie-reply/reply.md` for the source discussion.

## When to choose `screen_rect.for_accessible` vs the fallback

The function tries AT-SPI's `Component.get_extents(SCREEN)` first.
That path:

- Works for GTK3 / Qt5 / native X apps on X11.
- Works for accessibility-aware GTK4 apps when the SCREEN coord
  type is populated.
- Returns -1,-1 (or zero-width) for GTK4-on-XWayland that doesn't
  populate the screen-coord bridge, and for most Wayland apps.

The fallback path (`_try_window_relative_fallback`) handles the
"GTK4-on-X11 with broken SCREEN coords" case by:

1. Asking Gdk for the currently-active toplevel window's screen
   origin (X11 only).
2. Asking AT-SPI for the object's WINDOW-relative extents
   (which Atspi usually does return correctly even when SCREEN
   is broken).
3. Adding the window origin to the WINDOW offset.

This is best-effort: it assumes `obj` belongs to the currently-
active window. For OCR-style use cases ("OCR the focused text"),
that's correct. For unusual use cases (querying coords of an
inactive window's object), callers should compute the origin
themselves.

## Future work

- **v0.2: Wayland mouse synth.** xdg-desktop-portal `RemoteDesktop`
  interface. Requires a user-permission dialog handshake; the
  session token persists across calls within a session.
- **v0.3: Wayland screen rect.** Same portal can return cursor
  position; some compositors expose more via D-Bus extensions.
  Best-effort.
- **Liblouis-backed braille translation helper.** Currently lives
  in orca-remote's `braille_table.py` as a static ASCII table;
  belongs here once the dep tradeoffs are settled.
