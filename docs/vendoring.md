# Vendoring orca-ext-utils into an extension

The recommended way to ship orca-ext-utils functionality inside
an `.orca-ext` archive: copy the `orca_ext_utils/` package into
your extension's source tree, commit it, and import via relative
path. NVDA add-ons have shipped utilities this way for over a
decade; the pattern is reliable and the user installs one file.

## Why vendor instead of depending on a PyPI install

- **One install step for the user.** `orca --install-extension foo.orca-ext`
  and done. No `pip install orca-ext-utils` to forget. No version
  drift between users.
- **Failure isolation.** A bug in vendored screen-rect breaks the
  extension that shipped it; it does not break a sibling
  extension that vendored a different version of the same code.
- **No PyPI publication needed.** The library can stay as a
  GitHub project; you sync at a specific git tag.
- **Doesn't depend on Joanie's planned `requires-python-package` field.**
  That field would let extensions declare PyPI deps to Orca, but
  it doesn't exist yet -- vendoring works today regardless.

## The vendor workflow

### One-time setup in your extension repo

1. Create `vendor/` at the extension's root.
2. Pull this repo's `orca_ext_utils/` directory into
   `vendor/orca_ext_utils/`. Either:

```sh
# Option A: git subtree (preserves history, allows easy updates)
git subtree add --prefix vendor/orca_ext_utils \
    https://github.com/churst90/orca-ext-utils.git v0.1.0 --squash

# Option B: plain copy (simpler, no git plumbing)
git clone --depth 1 --branch v0.1.0 \
    https://github.com/churst90/orca-ext-utils.git /tmp/_oeu
cp -r /tmp/_oeu/orca_ext_utils vendor/orca_ext_utils
rm -rf /tmp/_oeu
```

3. Create `vendor/UPDATE.md` with the version pin (see template
   below).
4. Import in your extension code via the relative path:

```python
from .vendor.orca_ext_utils import screen_rect, mouse_input
```

5. Add `vendor/` to your build manifest so it ships in the
   `.orca-ext` archive (the default `build-orca-ext.sh` script
   includes everything that isn't `.pyc` / `__pycache__` /
   dotfiles, so no special handling is needed).

### `vendor/UPDATE.md` template

```markdown
# Vendored dependencies

## orca-ext-utils

- **Synced from:** https://github.com/churst90/orca-ext-utils
- **Version:** v0.1.0
- **Synced on:** 2026-06-15
- **Synced by:** <your-name>

## How to update

1. `git subtree pull --prefix vendor/orca_ext_utils \
       https://github.com/churst90/orca-ext-utils.git vX.Y.Z --squash`
   (or re-run the plain-copy steps in `docs/vendoring.md`)
2. Run the extension's test suite.
3. Update the `Version` and `Synced on` lines above.
4. Commit with a message referencing the version bump.
```

### Updating to a new release

```sh
# git subtree workflow
git subtree pull --prefix vendor/orca_ext_utils \
    https://github.com/churst90/orca-ext-utils.git v0.2.0 --squash
```

If you used the plain-copy workflow:

```sh
git rm -r vendor/orca_ext_utils
git clone --depth 1 --branch v0.2.0 \
    https://github.com/churst90/orca-ext-utils.git /tmp/_oeu
cp -r /tmp/_oeu/orca_ext_utils vendor/orca_ext_utils
git add vendor/orca_ext_utils
git commit -m "vendor: bump orca-ext-utils to v0.2.0"
```

## Sharing code between extensions

If extensions A and B both vendor v0.1.0 and a bug is fixed in
v0.1.1, A and B each have to bump independently. That's the
trade-off vendoring makes. The win is independence: A can ship
v0.1.1 fixes without B's maintainer agreeing.

If two extensions need to coordinate updates (e.g. shared protocol
constants), put those constants in a separate small package and
both extensions vendor it -- don't have A depend on B's vendored
copy.

## When NOT to vendor

If your extension is purely a development tool, or if you're
specifically targeting power-user extension authors who already
have a Python environment, install orca-ext-utils as a regular
Python package and import normally:

```sh
pip install --user orca-ext-utils  # once it's on PyPI
# or
pip install --user -e git+https://github.com/churst90/orca-ext-utils.git
```

Then:

```python
from orca_ext_utils import screen_rect
```

For everything else -- extensions intended for end users to
install via `orca --install-extension` -- vendor.
