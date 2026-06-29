# Contributing to Shell Sentinel

Thanks for considering a contribution.

## Documentation languages

Shell Sentinel maintains two documentation tiers:

### Project & collaboration (English only)

Keep these in **English** when you change them:

- `README.md` (canonical GitHub readme)
- `CHANGELOG.md`
- `CONTRIBUTING.md`, `SECURITY.md`, `CODE_OF_CONDUCT.md`
- `AGENTS.md`, `.github/copilot-instructions.md`
- `.github/` issue and PR templates
- `docs/README.md` (documentation index)

### Product & operations (English, Spanish, German)

Keep these **in sync across EN, ES, and DE** when behaviour or operator-facing flows change:

- `README_es.md`, `README_de.md`
- `docs/user_guide_en.md`, `docs/user_guide_es.md`, `docs/user_guide_de.md`
- `docs/dependencies_en.md`, `docs/dependencies_es.md`, `docs/dependencies_de.md`
- `website/manuals/` locale variants and `website/assets/js/translations.js`
- `conf/locales/en`, `conf/locales/es`, `conf/locales/de`

If a change is user-visible in the TUI or on the website, update all three product languages before merging. If it only affects contributors or CI, English project docs are enough.

## Ground rules

- Keep changes narrow and reviewable
- Update docs when behaviour changes (see language policy above)
- Do not commit secrets or credentials

## Before opening a pull request

- `make format`, `make lint`, and `make test` pass locally
- Lockfiles updated if `pyproject.toml` dependencies changed (`make lock`)
- Docs match the new behaviour in the correct language tier

## Pull request guidance

A good PR should explain:

- what changed
- why it changed
- how it was verified
- which documentation files were updated (and which locales)

## Issues before PRs

For larger changes, open an issue first so the direction can be aligned before implementation.

## Licensing note

By contributing, you agree that your contribution may be distributed under the repository licence.
