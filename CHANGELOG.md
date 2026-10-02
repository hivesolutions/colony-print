# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

* Restart of the nodes from the admin and the API, done only once their pending jobs are printed - [#34](https://github.com/hivesolutions/colony-print/issues/34)
* Update of the nodes from the admin and the API, even with their auto-update disabled - [#34](https://github.com/hivesolutions/colony-print/issues/34)
* Auto-update of the nodes enabled and disabled from the admin and the API - [#34](https://github.com/hivesolutions/colony-print/issues/34)
* Start time, auto-update and last update of the nodes in the admin node view - [#34](https://github.com/hivesolutions/colony-print/issues/34)
* Versions of the nodes before and after their restart in the admin job views - [#34](https://github.com/hivesolutions/colony-print/issues/34)
* Option to disable the remote control of a node in its configuration - [#34](https://github.com/hivesolutions/colony-print/issues/34)

### Changed

* Fonts of the print jobs skipped for the nodes that don't support them, that print the documents with their own fonts, instead of refusing the jobs - [#38](https://github.com/hivesolutions/colony-print/issues/38)

### Fixed

* Configuration file of the nodes ignored when their boot is run outside of the Windows service - [#34](https://github.com/hivesolutions/colony-print/issues/34)
* Updated nodes running with modules of the previous version when their boot is run outside of the Windows service - [#34](https://github.com/hivesolutions/colony-print/issues/34)
* Error message missing from the jobs refused by a node that lacks the capability they require - [#34](https://github.com/hivesolutions/colony-print/issues/34)

## [0.23.0] - 2026-10-02

### Added

* Capabilities of the nodes, advertised by each node and verified by the server before sending it a job - [#29](https://github.com/hivesolutions/colony-print/issues/29)
* Fonts sent with the print jobs of Binie and XMPL documents, installed on demand by the nodes without any manual install - [#29](https://github.com/hivesolutions/colony-print/issues/29)
* Printing of XMPL documents, converted into Binie documents by the nodes - [#29](https://github.com/hivesolutions/colony-print/issues/29)
* Capabilities and installed fonts of the nodes, and fonts of the jobs, in the admin UI - [#29](https://github.com/hivesolutions/colony-print/issues/29)
* Coverage report of the unit tests in the continuous integration
* Note on the printer settings used by the Windows node service, the `Printing Defaults` of the printer and not the `Printing Preferences` of a user
* Windows installer for the Windows XP nodes (`colony-print-node-setup-xp-<version>.exe`, 32 bit), which installs Python 2.7 with NSSM as the service wrapper, built, smoke tested and attached to the GitHub release of each version by the Windows workflow
* Self-update of the nodes that run Python 2.7 (the Windows XP ones), whose pip is not able to list the versions of a package

### Changed

* The Windows installers replace the node installed by the other installer (uninstalling it and keeping its configuration), as both use the same service

### Fixed

* Converted documents sent with the base64 content type even when not encoded in base64 - [#36](https://github.com/hivesolutions/colony-print/issues/36)
* Boot of the Windows nodes that run Python 2.7 failing with configuration values that are not ASCII (e.g. the name of the node)
* Jobs of the nodes that run Python 2.7 failing with printers whose name is not ASCII

## [0.22.0] - 2026-10-02

### Added

* Library versions and print diagnostics (job counts and last print) of the nodes in the admin node view - [#23](https://github.com/hivesolutions/colony-print/issues/23)
* Operating system information (system, distribution, version and architecture) of the nodes in the admin node view

### Fixed

* Jobs of a type not handled by the node reported as finished without being printed, now reported as errors

## [0.21.0] - 2026-10-02

### Added

* Linux nodes print the same Binie documents as Windows nodes, laid out for the paper and printable area of the printer - [#24](https://github.com/hivesolutions/colony-print/issues/24)
* Paper size (of PDF documents) and scaling print options for Linux printers - [#24](https://github.com/hivesolutions/colony-print/issues/24)
* Substitution of the fonts missing on Linux nodes by the closest installed font - [#24](https://github.com/hivesolutions/colony-print/issues/24)
* Review of every pull request by Claude
* Windows installer (`setup.exe`) for the nodes, which installs an embedded Python with colony-print, npcolony and their dependencies and runs the node as a Windows service
* Self-update of the Windows nodes from PyPI whenever their service starts, with optional version pins (`NODE_VERSION` and `NODE_NPCOLONY_VERSION`) and package index (`NODE_INDEX_URL`)
* Windows workflow that builds and smoke tests the node installer, attaching it to the GitHub release of each version

### Changed

* Print jobs on Linux printers are named after the job in the printer queue - [#24](https://github.com/hivesolutions/colony-print/issues/24)
* Binie documents on Linux nodes only use their own paper size when the printer accepts it as a custom size (as reported by a recent npcolony), otherwise they print on the default paper of the printer - [#26](https://github.com/hivesolutions/colony-print/issues/26)

### Fixed

* Result of the email mode jobs that save their output not reaching the server (as it was not JSON serializable) on Python 3 nodes
* Blank pages when printing PDF documents on recent Linux systems - [#24](https://github.com/hivesolutions/colony-print/issues/24)
* Email mode for Binie documents on Linux nodes - [#24](https://github.com/hivesolutions/colony-print/issues/24)
* Zero height pages when converting a document with only a width - [#24](https://github.com/hivesolutions/colony-print/issues/24)
* PDF generation failing on Python 3.5, 3.7 and 3.8 with the reportlab releases installed by default - [#24](https://github.com/hivesolutions/colony-print/issues/24)
* Labels split into several clipped pages on Linux printers without their paper size (e.g. A4 office printers), now printed at their real size in the top left corner as on Windows - [#26](https://github.com/hivesolutions/colony-print/issues/26)
* Labels of the paper loaded in Linux printers no longer spill their last millimeter onto another label - [#26](https://github.com/hivesolutions/colony-print/issues/26)

## [0.20.0] - 2026-06-17

### Added

* Support for the check path mode in gravo print jobs, tracing the engraving path with the laser light only

## [0.19.3] - 2026-06-14

### Fixed

* Faster job listing by dropping heavy result fields from each job

## [0.19.2] - 2026-06-14

### Fixed

* Correct decoding of the gravo print payload on Python 3.5 setups

## [0.19.1] - 2026-06-13

### Fixed

* Faster job listing by no longer retaining the decoded payload of each job
* Correct decoding of the job request payload on Python 3.5 setups

## [0.19.0] - 2026-06-09

### Added

* Optional `extra_fonts` field on the `gravo` print payload that ships per print job `.f3s` font payloads to the engraving software, staged on a per job temporary directory through a new `_stage_extra_fonts` helper and forwarded to gravo pilot's `extra_fonts` keyword argument; the staging directory is removed regardless of whether the print succeeds or raises ([#20](https://github.com/hivesolutions/colony-print/issues/20))

## [0.18.0] - 2026-06-04

### Added

* Ability to duplicate an existing print job, reusing its original payload, from both the API and the Admin UI
* Ability to download a print job's original payload from the Admin UI

## [0.17.0] - 2026-06-04

### Added

* OPTIONS handlers on every `/jobs` and `/jobs/<id>/...` route so browsers can complete the CORS preflight and reach the job status, cancel and files endpoints directly from a different origin, matching the pattern already in place for the `/nodes/<id>/print` routes.

## [0.16.1] - 2026-06-03

### Fixed

* Correct handling of file-based Gravo session recording videos when returning job results

## [0.16.0] - 2026-06-03

### Added

* CI step that deploys the `colony-print-latest` instance to the bemisc infrastructure on every push to `master`
* Support for the gravo `record` parameter, returning the session recording video alongside the job screenshots

## [0.15.0] - 2026-06-02

### Added

* CI job that builds a Docker image and deploys it to the bemisc infrastructure
* Ability to cancel queued print jobs

### Fixed

* Return empty list from `GET /printers` instead of 500 when the `npcolony` engine is not available

## [0.14.0] - 2026-03-12

### Added

* Margins parameter validation for Gravo Pilot print jobs

## [0.13.0] - 2026-03-12

### Added

* NPColony and Gravo Pilot version reporting in node engine info
* Gravo Pilot support for margins

## [0.12.0] - 2026-03-10

### Added

* Duration formatting and collapsible logs section with severity tags in job detail page

## [0.11.0] - 2026-03-10

### Added

* Separate request, response, and full payload sections in job detail page
* Collapsible payload sections in job detail page
* Strip result data field from in-memory job info

## [0.10.0] - 2026-03-10

### Added

* Job result files listing and download endpoints in Admin UI

## [0.9.0] - 2026-03-10

### Added

* Server info endpoint and display in settings page of Admin UI
* Duration formatting utility for uptime display
* Request payload storage and display for JSON-based jobs (e.g. gravo)
* Type and handler fields rendered as tags in job views

## [0.8.0] - 2026-03-09

### Added

* Raw JSON payload display in job detail page in Admin UI
* Traceback storage and display for failed print jobs in Admin UI
* Result column with colored tags in jobs list page in Admin UI

## [0.7.0] - 2026-02-26

### Added

* Node last seen timestamp tracking and display in Admin UI
* Job output file preview and download in Admin UI with encoding and MIME type display

## [0.6.0] - 2026-02-25

### Added

* Favicon for the Admin UI
* Job and node detail pages in the Admin UI
* Clickable job and node IDs linking to detail pages
* Mobile-friendly responsive layout for the Admin UI
* Collapsible sidebar with hamburger menu on mobile
* Card-based table layout for mobile viewports
* Node links in job listings and dashboard

### Fixed

* Admin UI client-side routing on page refresh using regex route matching

## [0.5.2] - 2026-02-24

### Fixed

* Use `python -m build` instead of `setup.py sdist bdist_wheel` in deploy workflow to fix PyPI filename rejection

## [0.5.1] - 2026-02-24

### Changed

* New deploy version, using Python 3.14

## [0.5.0] - 2026-02-24

### Added

* Admin UI sub-project (React + TypeScript + Parcel) under `frontends/admin/` - [#14](https://github.com/hivesolutions/colony-print/issues/14)
* AdminUIController to serve the SPA from `/admin-ui`
* Dashboard, Nodes, Jobs, Printers, and Settings pages
* Username/password authentication via Appier's built-in AdminPart

### Fixed

* Issues related to job info non existent for job

## [0.4.8] - 2025-01-19

### Changed

* Set safe sleep time to zero

## [0.4.7] - 2025-01-19

### Added

* More safeguards to PDF generation

## [0.4.6] - 2025-01-19

### Added

* New /ping route for health check

### Changed

* Small result values changes

## [0.4.5] - 2025-01-18

### Fixed

* Email receiver processing

## [0.4.4] - 2025-01-18

### Added

* Options for saving output and sending email in print jobs

## [0.4.3] - 2025-01-18

### Changed

* Improved options parsing

## [0.4.2] - 2025-01-18

### Fixed

* Issue related to email template and encoding

## [0.4.1] - 2025-01-18

### Changed

* Improved exception handling to add more verbosity

## [0.4.0] - 2024-06-03

### Added

* Support for new print job status visibility and result - [#7](https://github.com/hivesolutions/colony-print/issues/7)
* Support for plain `data` field encoding - [#10](https://github.com/hivesolutions/colony-print/issues/10)
* Support for gravo pilot printing - [#12](https://github.com/hivesolutions/colony-print/issues/12)

### Changed

* Created template content using ChatGPT

## [0.3.3] - 2024-05-02

### Changed

* Better support for email receiver processing

## [0.3.2] - 2024-05-01

### Fixed

* Busy waiting for the print job to finish

## [0.3.1] - 2024-05-01

### Added

* Support for email node mode

## [0.3.0] - 2024-04-30

### Changed

* Small README.md content change
* Changed code to make it Black compliant
* Support for options as part of the print params

## [0.2.0] - 2023-05-07

### Added

* Support for GitHub Actions

### Changed

* Repo name to `colony-print`
