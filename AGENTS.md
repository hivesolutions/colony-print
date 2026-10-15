# AGENTS.md file

## Python Virtual Environment (venv)

The Python virtual environment for this repository is typically located in `.venv`.

## Formatting

Always format the code before commiting using, making sure that the Python code is properly formatted using:

```bash
pip install black
black .
```

## Testing

To run the custom suite of unit test for Colony Print use the following sequence of commands that will install dependencies
and run the appropriate test suite (last command).

Try to run the unit tests whenever making changes to the codebase, before commiting new code.

```bash
pip install -r requirements.txt
pip install -r extra.txt
python setup.py test
```

The admin UI (`frontends/admin/`) has its own unit tests, under `react/test/` (mirroring the paths of the files they test), that run with Vitest and require Node.js 22.22 (or 24.15) and newer.

```bash
cd frontends/admin
npm install
npm test
npm test -- --coverage
```

## Style Guide

- Always update `CHANGELOG.md` according to semantic versioning, mentioning your changes in the unreleased section.
- Write commit messages using [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/).
- Never bump the internal package version in `setup.py`. This is handled automatically by the release process.
- Python files use CRLF as the line ending.
- The implementation should be done in Python 2.7+ and compatible with Python 3.13.
- No type annotations should exist in the `.py` files and if they exist they should be isolated in the `.pyi` files.
- The style should respect the black formatting.
- The implementation should be done in a way that is compatible with the existing codebase.
- Prefer `not item in list` over `item not in list`.
- Prefer `item == None` over `item is None`.
- The commenting style of the project is unique, try to keep commenting style consistent.
- Use Python docstrings with the `:type:`, `:args:`, `:rtype:`, `:return:`, etc. structure and with a newline after the docstring end (`"""`).

## Brand

- The logo is the sliced C mark (`res/mark.svg`), the "colony print" logotype (`res/logotype.svg`) and their lockup (`res/logo.svg`), in ink `#17181c` (white on dark backgrounds) and mint `#0fa47a`, the mint being only used for the middle slice.
- The middle slice of the mark is shifted to the right, the one of the logotype is never shifted, so that its letters stay aligned and readable.
- In the admin UI use the `Logo` atom (`react/components/atoms/logo.tsx`), that draws the solid logotype below 48px of height (unless `sliced` is set), as the cuts of the sliced one blur at small sizes.

## Admin UI Icons

The admin UI (`frontends/admin/`) uses [Ionicons](https://ionic.io/ionicons) (MIT) for its icons. Browse them at <https://ionic.io/ionicons> to find their names.

- Install the `ionicons` package (8.x) in `frontends/admin`, never load it from a CDN, as the admin may be served without internet access.
- Render the icons with the `ion-icon` web component, registered once with `defineCustomElement()` from `ionicons/components/ion-icon.js`, giving it the icon data imported from `ionicons/icons` (e.g. `import { printOutline } from "ionicons/icons"` and `<ion-icon icon={printOutline} />`), so that only the icons in use are bundled and nothing is fetched at runtime.
- Don't use the data of `ionicons/icons` without the component (e.g. as an `<img>` or a CSS mask), as some icons rely on its styles (e.g. `server-outline` is drawn filled without the `ionicon-fill-none` class).
- Use the icons through a single `Icon` atom (`react/components/atoms/icon.tsx`, which also declares `ion-icon` in `JSX.IntrinsicElements`) taking the icon, its size and an optional label, hidden from screen readers (`aria-hidden`) when it has no label. Icon-only buttons need an `aria-label`.
- Use the outline variant (e.g. `print-outline`), the active states (e.g. the selected item of the side bar) being told apart by their color, never the filled or the sharp ones. Logos (e.g. `logo-windows`) only exist filled.
- Size the icons with the `size` of the `Icon` atom (`sm` of 14px in the buttons, the tables and the headers of the panels, `md` of 16px in the side bar and the top bar, `lg` of 20px for the menu toggle) and color them with `color`, as they're drawn with `currentColor`.
- Keep one icon per concept across the views:

| Concept                   | Icon                                                               |
| ------------------------- | ------------------------------------------------------------------ |
| Dashboard                 | `grid-outline`                                                     |
| Nodes, server             | `server-outline`                                                   |
| Jobs                      | `document-text-outline`                                            |
| Printers, `npcolony` jobs | `print-outline`                                                    |
| Settings                  | `settings-outline`                                                 |
| `gravo` jobs              | `diamond-outline`                                                  |
| Fonts, `fonts` jobs       | `text-outline`                                                     |
| Email mode                | `mail-outline`                                                     |
| Refresh                   | `refresh-outline`                                                  |
| Restart                   | `reload-outline`                                                   |
| Update, `update` jobs     | `cloud-download-outline`                                           |
| Auto-update               | `sync-outline`                                                     |
| Platform                  | `logo-windows`, `logo-tux`                                         |
| Location                  | `location-outline`                                                 |
| Success, error, in flight | `checkmark-circle-outline`, `alert-circle-outline`, `time-outline` |
| API health, last job      | `pulse-outline`                                                    |
| Breadcrumb, more          | `chevron-forward-outline`                                          |
| Capabilities              | `extension-puzzle-outline`                                         |
| Libraries                 | `library-outline`                                                  |
| Search                    | `search-outline`                                                   |
| Password visibility       | `eye-outline`, `eye-off-outline`                                   |
| API connection            | `link-outline`                                                     |
| Session, log out          | `person-outline`, `log-out-outline`                                |

## Commit Messages

This project follows [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) with the following structure:

```text
<type>: <description>

<body>
```

### Commit Types

| Type       | Description                                             |
| ---------- | ------------------------------------------------------- |
| `feat`     | A new feature or functionality                          |
| `fix`      | A bug fix                                               |
| `docs`     | Documentation only changes                              |
| `refactor` | Code change that neither fixes a bug nor adds a feature |
| `chore`    | Maintenance tasks, dependency updates, build changes    |
| `test`     | Adding or updating tests                                |
| `version`  | Version bump commits (reserved for releases)            |

### Guidelines

- Use lowercase for the type prefix.
- Use imperative mood in the description (e.g., "Add feature" not "Added feature").
- Keep the first line under 50 characters.
- Reference issue/PR numbers when applicable using `(#123)` at the end.
- For version releases, use the format `version: X.Y.Z`.
- Add an extra newline between subject and body.
- Make the body a series of bullet points about the commit.
- Be descriptive always making use of the body of the message.

### Examples

```text
feat: Add user authentication with OAuth 2.0 support (#138)
fix: Resolve race condition in database connection pool
docs: Add API endpoint documentation for v2 routes
refactor: Extract validation logic into reusable utility module
chore: Update dependencies to latest stable versions
test: Add integration tests for payment processing flow
version: 1.8.0
```

## Pre-Commit Checklist

Before committing, ensure that the following operations items check:

- [ ] Code is formatted with `black .`
- [ ] Tests pass: `python setup.py test`
- [ ] CHANGELOG.md is updated in [Unreleased] section
- [ ] No debugging print statements or commented-out code
- [ ] CRLF line endings are preserved
- [ ] No type annotations in .py files (use .pyi if needed)

## New Release

To create a new release follow the following steps:

- Make sure that both the tests pass and the code formatting are valid.
- Increment (look at `CHANGELOG.md` for semver changes) the `version` value in `setup.py`, then the `def _version(self):` return value in `src/colony_print/main.py`, and then the `VERSION` value in `src/colony_print/node.py`.
- Move all the `CHANGELOG.md` Unreleased items that have at least one non empty item the into a new section with the new version number and date, and then create new empty sub-sections (Added, Changed and Fixed) for the Unreleased section with a single empty item.
- Create a commit with the following message `version: $VERSION_NUMBER`.
- Push the commit.
- Create a new tag with the value fo the new version number `$VERSION_NUMBER`.
- Create a new release on the GitHub repo using the Markdown from the corresponding version entry in `CHANGELOG.md` as the description of the release and the version number as the title. Do not include the title of the release (version and date) in the description.
- Once the release is published, the `Windows Workflow` builds the installers of the Windows nodes (`colony-print-node-setup-$VERSION_NUMBER.exe` and `colony-print-node-setup-xp-$VERSION_NUMBER.exe`, the one of the Windows XP nodes) and attaches them to the release, there's no need to build or upload them by hand.

## License

Colony Print is licensed under the [Apache License, Version 2.0](http://www.apache.org/licenses/).
