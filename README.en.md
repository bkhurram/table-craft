<p align="center">
  <img src="assets/icons/elephant-craft.png" alt="TableCraft elephant icon" width="144">
</p>

<h1 align="center">TableCraft</h1>

<p align="center"><b>A workspace for SQL, tables and database connections on macOS.</b><br>
Local TablePlus customization with Craft branding, a separate profile and reproducible analysis tools.</p>

<p align="center"><a href="README.md">Italiano</a> · <a href="docs/setup.md">Setup</a> ·
<a href="docs/architecture.md">Architecture</a> · <a href="CONTRIBUTING.md">Contributing</a></p>

![Synthetic SQLite data with three combined filters](docs/images/sqlite-filters.png)

The local project can now embed the complete customized runtime in `runtime/`.
Launch with `Avvia TableCraft.command` without installing TablePlus. Run
`python3 scripts/portable_runtime.py package` to export a complete portable ZIP.
The GitHub source archive still excludes vendor binaries. See the
[portable runtime guide (Italian)](docs/portable-runtime.md).

## What this repository provides

TableCraft contains scripts that customize a separately installed copy of
TablePlus: application name, welcome screen, menus, elephant icon and profile.
The database engine and native interface come from the complete TablePlus bundle,
either embedded locally or copied from an installed application.

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
| TablePlus source | **27.0.2 (818)** and **27.1.0 (830)** supported by setup; 830 launch, profile and SQLite verified locally; see [report](docs/compatibility.md) |
| Local-control changes | Only **27.0.2 (818)**, exact executable SHA-256 required |
| macOS 12+ | Minimum declared by the source bundle; other OS versions not tested |
| Intel / Rosetta | Original slice exists; local-control changes and runtime not verified |
| Windows, Linux, web | No implementation in this repository |
| Databases | SQLite tested; other bundled adapters not verified end-to-end |
| AI, MCP, online services | Components observed; integrations and server entitlements not verified |
| Tools | Python **3.9+**, zsh and macOS copy/signing tools; Apple developer tools for optional analysis |

## Get started

With an embedded runtime or the portable ZIP, launch `Avvia TableCraft.command` directly.
For a source-only checkout without `runtime/`, install TablePlus separately at `/Applications/TablePlus.app`,
then download or clone this repository and run:

```sh
./scripts/setup_tablecraft.sh --check
./scripts/setup_tablecraft.sh
./"Avvia TableCraft.command"
```

You can also open `Avvia TableCraft.command` directly: on first launch it runs
setup automatically, provided the requirements above are installed. The GitHub
ZIP does not include the prepared application.

Default setup checks branding resources across builds. Exact source version and
hash are required for `--local-controls`. Build 802 has not been tested end-to-end here.
Setup preserves the original installation,
refuses to overwrite an existing local copy without `--update` and signs the copy ad hoc.
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

For the exact ARM64 **27.1.0 (830)** sample, `./scripts/setup_tablecraft.sh --update --workspace-limits` explicitly applies the local tab/workspace changes
while preserving the previous bundle and backing up the profile. Close
TableCraft first. Four SQL tabs and three simultaneous SQLite workspaces were
verified offline with synthetic data. This option does not change license-state
presentation or remote database permissions. A plain update restores the vendor
controls. See [setup details](docs/setup.md#schede-e-workspace-sulla-build-830).

Original repository code is [MIT licensed](LICENSE). This does not license
TablePlus or its resources; see [NOTICE](NOTICE). The elephant was generated with
ImageGen; provenance is documented in [branding notes](docs/branding.md).

README presentation was inspired by [PDFCraft](https://github.com/storytold/pdfcraft).
[awesome-reverse-engineering](https://github.com/morluto/awesome-reverse-engineering)
provided the analysis-tool reference. TableCraft is independently maintained and
is not affiliated with TablePlus, PDFCraft or ArtCraft.

## Update compatibility and profile persistence

Both TablePlus 27.0.2 (818) and 27.1.0 (830) are supported by the branding
installer. The 830 bundle passed resource validation, signing, launch and a
synthetic SQLite read/filter smoke test on this Mac. See the
[compatibility report](docs/compatibility.md) for the limits of that evidence.
The standalone AboutWindow.nib is absent in 830; it remains required for 818.

Close TableCraft, then run `./scripts/setup_tablecraft.sh --update` and reopen
the launcher. This rebuilds branding from the installed original, snapshots
the profile, and retains the previous application in `analysis/copies/previous.*/`.
The existing license-control patches are not migrated by this update.

The launcher now uses a stable profile in
`~/Library/Application Support/TableCraft/runtime-profile/`. On first use it
copies the legacy checkout's `analysis/runtime-profile/` without deleting it.
An existing stable profile always wins; profiles are never automatically merged.
An absolute `TABLECRAFT_PROFILE` overrides the default. Backups are stored in
`profile-backups/` beside the selected profile and contain private data.

Premium access requires a valid vendor license and activation on the destination
Mac. It is not granted by this installer. No second Mac was available for a
runtime/activation test. Keychain passwords, external SSH keys and database
files must be migrated separately through supported tools.
