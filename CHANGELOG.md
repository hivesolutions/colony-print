# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

* Admin UI sub-project (React + TypeScript + Parcel) under `frontends/admin/` - [#14](https://github.com/hivesolutions/colony-print/issues/14)
* AdminUIController to serve the SPA from `/admin-ui`
* Dashboard, Nodes, Jobs, Printers, and Settings pages
* Username/password authentication via Appier's built-in AdminPart

### Changed

*

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
