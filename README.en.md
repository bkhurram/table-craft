<p align="center">
  <img src="assets/icons/elephant-craft.png" alt="TableCraft elephant icon" width="144">
</p>

<h1 align="center">TableCraft</h1>

<p align="center"><b>A workspace for SQL, tables and database connections on macOS.</b><br>
Local TablePlus customization with Craft branding, a separate profile and reproducible analysis tools.</p>

<p align="center"><a href="README.md">Italiano</a> · <a href="docs/setup.md">Setup</a> ·
<a href="docs/architecture.md">Architecture</a> · <a href="CONTRIBUTING.md">Contributing</a></p>

![Synthetic SQLite data with three combined filters](docs/images/sqlite-filters.png)

## What this repository provides

TableCraft contains scripts that customize a separately installed copy of
TablePlus: application name, welcome screen, menus, elephant icon and profile.
The database engine and native interface come from the installed application.

The TablePlus application, its source code, vendor resources and user profiles
are not distributed here. This repository does not build a standalone database
client from source.

## Features

- Consistent Craft branding across the macOS icon and internal screens.
- Separate local connection and preferences profile.
- SQL tabs, table browsing, filters and Metrics Boards provided by the base app.
- Read-only bundle analysis, dependency inventory, hashes and LLDB inspection.
- Optional local-control research changes pinned to one executable hash.

SQLite query execution, three simultaneous workspaces, multiple SQL tabs, three
combined filters and two Metrics Boards were verified in the local research
sample. These observations do not establish that every Premium or online feature
is unlocked. The default setup applies branding; research control changes are opt-in.

## Compatibility

| Component | Status |
|---|---|
| macOS / Apple Silicon | Tested on macOS **27.0.1**, build **26A434**, ARM64 |
| TablePlus source | **27.0.2**, build **818**, exact executable SHA-256 required |
| macOS 12+ | Minimum declared by the source bundle; other OS versions not tested |
| Intel / Rosetta | Original slice exists; local-control changes and runtime not verified |
| Windows, Linux, web | No implementation in this repository |
| Databases | SQLite tested; other bundled adapters not verified end-to-end |
| AI, MCP, online services | Components observed; integrations and server entitlements not verified |
| Tools | Python **3.11+**, zsh and Apple developer tools |

## Get started

Install the supported TablePlus version separately at `/Applications/TablePlus.app`,
then download or clone this repository and run:

```sh
./scripts/setup_tablecraft.sh --check
./scripts/setup_tablecraft.sh
./"Avvia TableCraft.command"
```

You can also open `Avvia TableCraft.command` directly: on first launch it runs
setup automatically, provided the requirements above are installed. The GitHub
ZIP does not include the prepared application.

Setup checks the source version and hash, preserves the original installation,
refuses to overwrite an existing local copy and signs the copy ad hoc.
Automatic updates are disabled on the customized copy.

See [setup notes](docs/setup.md) for research options, offline mode and a synthetic
SQLite demo. There is no prebuilt application download in this repository.

## Repository and contributions

Public files include scripts, original branding assets, documentation and demo
screenshots. The `analysis/` folder, local app, profiles and raw evidence stay
outside Git. CI checks syntax, local documentation links and the indexed file set;
it does not build or fully test TablePlus.

Read [CONTRIBUTING.md](CONTRIBUTING.md), [publishing notes](docs/publishing.md)
and the [changelog](CHANGELOG.md).

## Credits and license

Original repository code is [MIT licensed](LICENSE). This does not license
TablePlus or its resources; see [NOTICE](NOTICE). The elephant was generated with
ImageGen; provenance is documented in [branding notes](docs/branding.md).

README presentation was inspired by [PDFCraft](https://github.com/storytold/pdfcraft).
[awesome-reverse-engineering](https://github.com/morluto/awesome-reverse-engineering)
provided the analysis-tool reference. TableCraft is independently maintained and
is not affiliated with TablePlus, PDFCraft or ArtCraft.
