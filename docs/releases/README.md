# Release Notes Policy

Tagged releases must include human-readable notes so operators know what changed.

Accepted locations for tag `vX.Y.Z`:

- `docs/releases/vX.Y.Z.md` (preferred)
- `releases/vX.Y.Z.md`
- `CHANGELOG.md` heading like `## [vX.Y.Z]` (or `## vX.Y.Z`)

Automation:

- `.github/workflows/release-check.yml` runs on tag pushes and fails if no notes
  source is found for the tag.
- Manual check helper: `python scripts/check_release_notes.py --tag vX.Y.Z`
