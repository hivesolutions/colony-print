# [Colony Print Infra-structure](http://colony-print.hive.pt)

Small web app for printing Colony-based documents.

This project includes two main components:

* The Web App end-point that provides XML to Binie conversion `colony_print.controllers`
* The structure conversion infra-structure (Visitors, AST, etc.) `colony_print.printing`

## Features

* Cloud printing, with minimal configuration
* Multiple engine support (npcolony, gravo, text)
* XMPL to Binie conversion
* XMPL printing, with the documents converted into Binie by the nodes
* PDF generation with custom fonts and images
* Fonts sent with the print jobs, installed on demand by the nodes
* Node capabilities, advertised by the nodes and verified by the server
* [GDI](https://en.wikipedia.org/wiki/Graphics_Device_Interface) printing (Windows) via [Colony NPAPI (npcolony)](https://github.com/hivesolutions/colony-npapi)
* [CUPS](https://en.wikipedia.org/wiki/CUPS) printing (Linux) via [Colony NPAPI (npcolony)](https://github.com/hivesolutions/colony-npapi)
* Windows installer for the nodes, which update themselves from PyPI (see [Windows Node](#windows-node))
* Restart and update of the nodes from the admin UI and from the API (see [Node Control](#node-control))

## Binie Specification

For a detailed understanding of the Binie file format used in this project, refer to the [Binie File Format Specification](doc/binie.md). This document outlines the structure and organization of the Binie file format, which is essential for developing compatible applications and tools.

## XMPL Specification

The XML Markup Language for Printing (XMPL) is integral to our document processing pipeline. For an in-depth understanding of the XMPL structure and its seamless convertibility to Binie, see the [XMPL File Format Specification](doc/xmpl.md).

## Node Capabilities

The features supported by each node (e.g. `xmpl` or `dynamic-fonts`) are advertised by the node as capabilities, and the requests that need a capability the node doesn't advertise are refused. The complete list of capabilities is described in [Node Capabilities](doc/capabilities.md).

## Installation

### Pre-requisites

```bash
apt-get install gcc python-dev
pip install --upgrade appier netius pillow reportlab
```

### Run Server

```bash
pip install colony_print
python -m colony_print.main
```

### Run Node

```bash
pip install colony_print
BASE_URL=$BASE_URL \
SECRET_KEY=$SECRET_KEY \
NODE_ID=$NODE_ID \
NODE_NAME=$NODE_NAME \
NODE_LOCATION=$NODE_LOCATION \
python -m colony_print.node
```

The node may also be run by its boot, which loads the configuration of the node from a `config.env` file (the values of the environment take precedence), updates colony-print and npcolony from PyPI (see [Self-Update](#self-update)) and then runs the node, as the service of the Windows nodes does. It's the way to run the nodes that are updated from the admin (see [Node Control](#node-control)), unless the boot is told to skip the update (`--no-update`):

```bash
pip install colony_print
python -m colony_print.boot --config config.env
```

The fonts installed on demand by the node (see [Print Fonts](#print-fonts)) are kept in the `FONTS_PATH` directory (defaults to `~/.colony_print/fonts`, and to the `fonts` directory of the data directory on the Windows nodes, see [Windows Node](#windows-node)), with each font file limited to `FONT_MAX_SIZE` bytes (defaults to 16 MB).

### Fonts

To be able to use new fonts (other than the ones provided by the system), one must install them into the `/usr/share/fonts/truetype` directory so they are exposed and ready to be used by the PDF generation infra-structure. For example, Calibri is one type of font that should be exported to a UNIX machine as many colony-generated documents use it.

The `/usr/share/fonts/truetype` install path is shared by the PDF generation engine.
Linux (CUPS) nodes need the same fonts to lay out the Binie documents they print. They look for the font files by name in the same paths and, as Windows does, fall back to the closest installed font found through fontconfig (`fc-match`), so installing Calibri (or the metric compatible Carlito font) keeps the layout identical to the Windows one. The same applies to the barcode fonts of the documents (e.g. the `2 of 5` font of the Omni product labels, looked up as `2 of 5.ttf`), whose barcodes are otherwise printed as the letters they are encoded with.
Binie and XMPL documents may also send their fonts with the print job (see [Print Fonts](#print-fonts)), so that nodes with the `dynamic-fonts` capability install them on demand, on Windows and Linux alike, without any manual install.
The `gravo` engine receives its fonts on a per print job basis through the `extra_fonts` field of the gravo print payload (see [Gravo Print Payload](#gravo-print-payload)) and stages them on a per job temporary directory, so the two flows are independent and operators should not confuse them.

### Engines

There are currently three engines available for printing in Colony Print:

* `npcolony` - The [Colony NPAPI](https://github.com/hivesolutions/colony-npapi) engine, which is used for GDI printing on Windows and CUPS printing on Linux.
* `gravo` - Which allows engraving of text and signatures using [Gravo Pilot](https://github.com/hivesolutions/gravo-pilot). Accepts an `extra_fonts` mapping in the print payload to ship `.f3s` font payloads to the engraving software on a per print job basis (see [Gravo Print Payload](#gravo-print-payload)).
* `text` - A simple virtual printer text engine that prints text to a simple plain text file and returns the file.

### Print Request

Every engine is reached through the same print endpoint and request envelope. A job is submitted to `/nodes/<id>/print` (or `/nodes/<id>/printers/<printer>/print` to target a specific printer) with the following fields:

| Field      | Type   | Required | Notes                                                                                                                      |
| ---------- | ------ | -------- | -------------------------------------------------------------------------------------------------------------------------- |
| `data`     | string | yes\*    | Raw document data, base64 encoded by the server before dispatch. Mutually exclusive with `data_b64`.                       |
| `data_b64` | string | yes\*    | Base64 encoded document data, the engine specific payload described below. Mutually exclusive with `data`.                 |
| `name`     | string | no       | Human readable job name. Defaults to the generated job identifier.                                                         |
| `type`     | string | no       | Target engine: `npcolony` (default), `gravo` or `text`, or `fonts` to install fonts. See [Print Fonts](#print-fonts).      |
| `format`   | string | no       | Expected document format (e.g. `binie`, `pdf` or `xmpl`). Validated against the node format when provided.                 |
| `options`  | object | no       | Extra per job options (see table below). Keys outside the supported set are discarded.                                     |
| `fonts`    | array  | no       | Fonts of the document (`binie` and `xmpl` formats only), installed on demand by the node. See [Print Fonts](#print-fonts). |

\* Exactly one of `data` or `data_b64` must be provided.

The `options` map is filtered to the following keys:

| Option            | Type    | Scope      | Notes                                                                                      |
| ----------------- | ------- | ---------- | ------------------------------------------------------------------------------------------ |
| `scale`           | number  | npcolony   | Accepted for compatibility, currently not applied by the npcolony engine.                  |
| `quality`         | number  | npcolony   | Accepted for compatibility, currently not applied by the npcolony engine.                  |
| `media`           | string  | npcolony   | Paper size requested to CUPS (e.g. `80x297mm`, `RP80x297` or `Custom.80x200mm`).           |
| `scaling`         | string  | npcolony   | CUPS print scaling: `auto`, `auto-fit`, `fit`, `fill` or `none`.                           |
| `save_output`     | boolean | email mode | When `true` the generated PDF is returned (base64) in the job result. Defaults to `false`. |
| `send_email`      | boolean | email mode | Whether to send the result email. Defaults to `true`.                                      |
| `email_address`   | string  | email mode | Single recipient address (alias of `email_receiver`).                                      |
| `email_receiver`  | string  | email mode | Single recipient address.                                                                  |
| `email_receivers` | array   | email mode | List of recipient addresses.                                                               |
| `email_override`  | boolean | email mode | When `true` the provided receivers replace the node default receivers. Defaults to `true`. |

The `save_output` and `email_*` options only take effect on nodes running in `email` mode (`NODE_MODE=email`).

The requests that use a feature that requires a capability the node doesn't advertise (e.g. the `xmpl` format or the `fonts` field) fail with `409`, see [Node Capabilities](doc/capabilities.md).

### npcolony Print Payload

The `npcolony` engine is the default and prints through [Colony NPAPI](https://github.com/hivesolutions/colony-npapi) using GDI on Windows and CUPS on Linux. Its payload is the binary print document carried in `data_b64`, typically a [Binie](doc/binie.md) document produced by the XMPL to Binie conversion, dispatched directly to the target printer. There are no JSON fields: the printing behaviour is tuned through the options and the optional `format` field described in [Print Request](#print-request).

On Windows the Binie document is drawn directly through GDI. Linux (CUPS) nodes only print PDF documents, so they convert Binie jobs (with the `binie` format, or without a format when the payload is a valid Binie document) into a PDF laid out with the same rules as GDI: the paper size of the document when it defines one and the printer accepts it as a custom paper size (as the Windows driver of the printer does), and the printer's default paper size otherwise (e.g. a label printed on an A4 printer comes out at its real size in the top left corner of the page), with the content laid out from the top left corner of the printable area of the page and printed without scaling. The `media` option doesn't apply to them, as their pages are always laid out for that paper size. PDF documents and any other data are sent to CUPS untouched.

XMPL documents (with the `xmpl` format) are converted into Binie documents by the nodes with the `xmpl` capability, and then printed as any other Binie document. The document is verified (converted) by the server when the job is submitted, so that an invalid document fails with `400`, and the fonts declared by its `font` elements (see [XMPL Specification](doc/xmpl.md)) are installed together with the ones of the `fonts` field. Only inline images (`source`) are accepted, the documents with image paths (`path`) are refused by the server and by the nodes, as the paths would be read from the file system of the node.

### Linux (CUPS) Printing

The printer of the job (or `NODE_PRINTER` when the job has none) selects the CUPS queue, and `default`, the default value of `NODE_PRINTER`, selects the default queue (or the only queue, when none is the default). Jobs for a queue that does not exist, or that CUPS refuses, fail with an error instead of being reported as printed.

Each queue should use a driver for its printer and a default paper size that matches the loaded paper, as that size is used for the Binie documents that do not define one, or whose size the printer does not accept as a custom paper size (e.g. `lpadmin -p receipt -o PageSize=RP80x297`):

* Receipt printers - the vendor CUPS driver (e.g. the Epson TM series driver), with its paper reduction options enabled to avoid feeding blank paper at the end of the receipt.
* Label printers - the label drivers shipped with CUPS (Zebra, Dymo) or the vendor ones, with the default size set to the loaded label.
* Office printers - driverless (IPP Everywhere) queues.

The custom paper sizes a printer accepts, and their margins, are the ones of the PPD of its queue, as reported by npcolony. With npcolony versions that don't report them, a Binie document only uses its own size when it matches the default paper size of the queue.

In `email` mode the PDF document is written to the output file (print to file) instead of being printed, as it happens with the PDF printer on Windows.

### Print Fonts

The fonts of a Binie or XMPL document may be sent in the `fonts` field of the print request, so that the nodes with the `dynamic-fonts` capability install them on demand before printing the document. The fonts (and the XMPL documents) are only accepted for the jobs of the `npcolony` type, as the other engines don't use them. Each entry of the `fonts` array accepts the following fields:

| Field      | Type   | Required | Notes                                                                                                                                           |
| ---------- | ------ | -------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| `name`     | string | yes      | Family name of the font as the document uses it (e.g. `2 of 5`), at most 31 characters. Must match the (Windows) family name of the font file.  |
| `style`    | string | no       | `regular`, `bold`, `italic` or `bold_italic`. Read from the font file when omitted, verified against it otherwise.                              |
| `data_b64` | string | yes\*    | Base64 encoded TrueType font file.                                                                                                              |
| `url`      | string | yes\*    | `http` or `https` URL of the TrueType font file, downloaded by the node.                                                                        |
| `md5`      | string | yes\*    | Hexadecimal MD5 of the font file. When alone it references a font already installed on the node, otherwise it's verified against the font file. |

\* Exactly one of `data_b64` or `url` (with an optional `md5` that is verified against the font file), or `md5` alone (a reference to a font installed on the node).

* Only TrueType fonts are supported (single fonts with TrueType outlines), OpenType fonts with PostScript (CFF) outlines and font collections are refused.
* The nodes keep the installed fonts in a cache that never expires, by the MD5 of their files, and download the font of a URL only once (URLs are considered immutable, so a changed font must be published at a new URL).
* The installed fonts are available to every later job of the node, as the fonts installed in the system are, and they are used before the system ones. When several files of the same family and style are installed, the most recently installed (or referenced) one is used.
* A font that can't be installed (download failure, MD5 not installed or not matching, not TrueType, license that doesn't allow embedding the font, name or style not matching the font file, larger than `FONT_MAX_SIZE`) fails the job with an error that names it, the fonts are never silently replaced by other fonts.
* On Linux (CUPS) the fonts are embedded in the PDF document, on Windows they're loaded in the system for the node process only, so no administration rights are required.
* On Windows the font files are parsed by the font engine of the system (in kernel mode before Windows 10, eg: Windows XP), so fonts should only be sent by trusted clients, as the admin token they require already implies.

The fonts installed on a node are listed by `GET /nodes/<id>/fonts`, and may be installed before any job (so that later jobs reference them by `md5` alone or not at all) by `POST /nodes/<id>/fonts`, with the same `fonts` array (`data_b64` or `url` entries), which queues a job of the `fonts` type whose result lists the installed fonts. The same job may also be sent to the print endpoints, with the `fonts` type and a `{"fonts": [...]}` JSON payload with the same entries.

The server side conversion of XMPL documents into PDF (`/documents.pdf`) also uses the fonts declared by the documents, installed in the font cache of the server (in `FONTS_PATH`, defaulting to the `fonts` directory of `DATA_PATH`), which requires the admin token.

### Gravo Print Payload

The `gravo` engine accepts a JSON payload submitted as base64 to the print endpoint. The accepted fields are documented below:

| Field         | Type            | Required | Notes                                                                                                                                                                                                                                       |
| ------------- | --------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `text`        | string or array | yes      | Either a plain string for single font runs or a multifont array of `[font, char]` pairs for mixed font runs.                                                                                                                                |
| `font`        | string          | no       | Default font name. Defaults to `HELVETICA 1L`.                                                                                                                                                                                              |
| `font_size`   | number          | no       | Default font size in the engraving software's unit.                                                                                                                                                                                         |
| `width`       | number          | no       | Engraving area width. Defaults to `80`.                                                                                                                                                                                                     |
| `height`      | number          | no       | Engraving area height. Defaults to `100`.                                                                                                                                                                                                   |
| `margins`     | array           | no       | Four element `[left, right, top, bottom]` margin array.                                                                                                                                                                                     |
| `dry_run`     | boolean         | no       | When `true` the engraving job is composed but not sent to the machine. Defaults to `false`.                                                                                                                                                 |
| `record`      | boolean         | no       | When `true` a video of the engraving session is captured and returned with the screenshots. Defaults to `false`.                                                                                                                            |
| `check_path`  | boolean         | no       | When `true` the engraving path is traced with the laser light only, without engraving the material, for test verification. Defaults to `false`.                                                                                             |
| `debug`       | boolean         | no       | When `true` the response includes the captured gravo pilot logs. Defaults to `false`.                                                                                                                                                       |
| `extra_fonts` | object          | no       | Mapping of font name to the base64 encoded `.f3s` payload that should be installed for the duration of the engraving session. Each entry is staged on a per job temporary directory and forwarded to gravo pilot's `extra_fonts` parameter. |

### Text Print Payload

The `text` engine is a virtual printer that does not talk to any physical device. Its payload is the plain text content carried in `data_b64`; the engine writes it to a `document.txt` file and returns that file (base64 encoded) in the job result. It has no JSON fields and ignores the printer, format and option values, which makes it convenient for testing and for capturing print output without hardware.

### Node Control

The nodes are restarted and updated from the admin UI (the node view) and from the API, without a session on their machines. The actions reach the node as jobs without data, through the queue of jobs it already polls, so they're listed with the other jobs and may be cancelled while queued:

| Endpoint                       | Job type      | Capability    | Notes                                                                                                                 |
| ------------------------------ | ------------- | ------------- | --------------------------------------------------------------------------------------------------------------------- |
| `POST /nodes/<id>/restart`     | `restart`     | `restart`     | Starts the process of the node again.                                                                                 |
| `POST /nodes/<id>/update`      | `update`      | `update`      | Restarts the node, which updates colony-print and npcolony on the way up, even with its auto-update disabled.         |
| `POST /nodes/<id>/auto_update` | `auto-update` | `auto-update` | Sets if the node updates its packages every time it starts, with the `enabled` field (`1` or `0`), without a restart. |

* Each endpoint requires the admin token and the capability of the node with the same name (see [Node Capabilities](doc/capabilities.md)), failing with `409` when the node doesn't advertise it, as the older nodes and the ones that never registered.
* A node with a `restart` or `update` job queued or in flight doesn't get another one, the request returns that job. An update requested while a restart is pending is then not run, as told by the `type` of the returned job, and must be requested again once the node is back.
* The node only restarts once the remaining jobs it has received are printed and their results posted, so no print is interrupted. The jobs queued meanwhile stay in the server until the node is back.
* A `restart` or `update` job is finished by the server when the node registers itself again with another start time (the one of its new process), with the version and the libraries of the node before and after in its result. Until then the job stays in `printing`, so a node that didn't come back is visible. An `update` job finishes as an error when the packages could not be updated, with the node running the installed ones.
* The commands carry no packages, versions or package index: what gets installed is the one of the configuration of the node (`NODE_VERSION`, `NODE_NPCOLONY_VERSION` and `NODE_INDEX_URL`, see [Self-Update](#self-update)), so the server only triggers what the node would do by itself.
* These jobs are left out of the print statistics of the node and can't be duplicated.

What a node supports depends on how it's run, as a running node can't update itself (the update is a restart whose boot updates the packages):

| Node                                                                           | `restart`    | `update` and `auto-update`                     |
| ------------------------------------------------------------------------------ | ------------ | ---------------------------------------------- |
| Windows service installed by the installer of this version                     | Yes (`exit`) | Yes                                            |
| Windows service installed by an older installer (once it updates itself)       | Yes (`exit`) | No, until the installer of this version is run |
| Run by the boot in any other way (e.g. `python -m colony_print.boot`, systemd) | Yes (`exec`) | Yes                                            |
| Run without the boot (`python -m colony_print.node`)                           | Yes (`exec`) | No                                             |

On Windows, the nodes that are not run by the Windows service of the installer only restart with `NODE_RESTART` set, as explained below.

The remote control of a node is configured in its configuration (`config.env` or the environment):

| Configuration  | Notes                                                                                                                                       |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| `NODE_RESTART` | How the node restarts, `exit` or `exec`, any other value (e.g. `0`) refusing the restart (and the update), which are then not advertised.   |
| `NODE_CONTROL` | `0` disables the three actions: the node advertises none of their capabilities and ignores the state file. The server can't enable it back. |

* `exit` - the process ends with an error exit code (`75`) and its service starts it again. It's the default for the nodes run by the Windows service of the installers, whose recovery actions (the ones of WinSW) restart it after 10, 30 and then 60 seconds (for the restarts within one hour), Windows logging it as a failure of the service.
* `exec` - the node runs its own command line again, with the environment it was started with, so that a changed `config.env` applies. It's the default for every other node, except on Windows. On Linux the process is replaced and keeps its PID, so it works for the nodes started by hand and under any supervisor (e.g. systemd or a container). On Windows a process can't be replaced, so a new one is started and the current one exits, which runs the node twice when something else also starts it again (e.g. a script loop or another service wrapper, the case `NODE_RESTART=exit` is for). For that reason a Windows node that is not run by the Windows service has no default: it's only restarted from the admin with `NODE_RESTART` set (to `exec` for a node started by hand).

The values set from the admin are kept in a `state.env` file next to `config.env`, written by the node and applied by the boot over the configuration, as the node never writes `config.env` (which holds the secret key): the auto-update (`NODE_UPDATE`, taking precedence over the one of the configuration) and the update forced for the next start (`NODE_UPDATE_ONCE`, removed by the boot once read). The node reports its start time (`start_time`) and the outcome of the update run by its boot (`update`, with `auto`, `status`, `time` and `error`) in its information.

Any admin token is able to restart and update the nodes, as it's able to print on them.

## Windows Node

Windows 10 and 11 (64 bit) nodes are installed with a `setup.exe` installer. It installs everything the node needs: an embedded Python, colony-print, [Colony NPAPI (npcolony)](https://github.com/hivesolutions/colony-npapi) for the native (GDI) printing, and their dependencies. The node runs as the `colony-print-node` Windows service, which starts with the machine and updates itself from [PyPI](https://pypi.org) every time it starts. The older versions of Windows (from Windows XP on) and the 32 bit ones have their own installer (see [Windows XP](#windows-xp)).

### Building the Installer

```powershell
.\windows\build.ps1 -Python C:\Python314\python.exe
```

The build requires a 64 bit Python (the embedded Python is the same version), whose version must have the digest of its embedded distribution pinned in `build.ps1` (currently 3.14.8, the digest of another version is published by python.org), and [Inno Setup 6](https://jrsoftware.org/isinfo.php), as npcolony and the other dependencies are installed from their PyPI wheels (nothing is compiled). It creates the installer (`dist\colony-print-node-setup-<version>.exe`), which bundles the packages, so that it installs the node without internet access. The `Windows Workflow` builds it on every push (the `colony-print-node-windows` artifact) and smoke tests the installer on a Windows runner. When a release is published, it also attaches the installer to the release, for which the tag of the release must match the version in `setup.py` (e.g. `0.21.0`). A failed attach can be retried by running the workflow manually with the tag of the release.

### Installing

The installer asks for the server URL and the secret key, which it verifies against the server. It then asks for the mode (`normal` or `email`), the node name, location and printer, and, in email mode, the email receivers and the Mailme key. The node ID is derived from the name and kept on later installs. It may also run silently (e.g. for mass deployment), with the configuration given as parameters:

```powershell
colony-print-node-setup-0.20.0.exe /VERYSILENT /URL=https://print.example.com/ /KEY=$SECRET_KEY /NAME="Shop 1" /LOCATION=Porto /PRINTER="EPSON TM-T20II Receipt"
```

| Parameter    | Configuration          | Notes                                                                            |
| ------------ | ---------------------- | -------------------------------------------------------------------------------- |
| `/URL`       | `BASE_URL`             | URL of the Colony Print server.                                                  |
| `/KEY`       | `SECRET_KEY`           | Secret key of the server, written to the setup log with `/LOG` (see `/CONFIG`).  |
| `/NAME`      | `NODE_NAME`            | Defaults to the computer name.                                                   |
| `/ID`        | `NODE_ID`              | Defaults to the name in lower case, with dashes (e.g. `shop-1`).                 |
| `/LOCATION`  | `NODE_LOCATION`        | Optional.                                                                        |
| `/PRINTER`   | `NODE_PRINTER`         | Printer of the jobs that don't select one.                                       |
| `/MODE`      | `NODE_MODE`            | `normal` (default) or `email`.                                                   |
| `/EMAILS`    | `NODE_EMAIL_RECEIVERS` | Email receivers, separated by `;` (email mode).                                  |
| `/MAILMEKEY` | `MAILME_KEY`           | Mailme key (email mode).                                                         |
| `/MAILMEURL` | `MAILME_BASE_URL`      | Optional Mailme URL (email mode).                                                |
| `/CONFIG`    |                        | Path to a `config.env` file with the values of the parameters that aren't given. |

The parameters that aren't given keep the values of the existing configuration, so running a new installer over a node only replaces its files. The installer exits with code `10` when the service could not be installed or started.

The service runs under the system account, so it only sees the printers installed for all users and has no default printer. The installer suggests the default printer of the user running it, and the printer should be set, otherwise the jobs that don't select one fail. In email mode the printer must be a PDF printer (e.g. `Microsoft Print to PDF`), as the jobs are printed to PDF files.

The service also prints with the settings of the printer that apply to all users (`Printer properties`, `Advanced`, `Printing Defaults`), and not with the `Printing Preferences` of a user, as Windows keeps them per user. A node that used to run under a user account (e.g. from a script) may print with other settings once it's installed as a service (e.g. the label size, the orientation or the offsets of a label printer, moving the content of the labels), in which case the values of the `Printing Preferences` of that user should be copied to the `Printing Defaults` of the printer.

The node is installed in `C:\Program Files\Colony Print Node` (other directories are refused, as the service runs its files as the system account). Its configuration (`config.env`), logs and fonts installed on demand (`fonts`) are in `C:\ProgramData\Colony Print Node`, which only the system account and the administrators can access, as it holds the secret key. A data directory (or configuration) owned by, or accessible to, any other user (e.g. created by a user before the install) is never used, the installer removes it and creates the data directory already restricted. The installer verifies the owner and the access with PowerShell when the service isn't installed, and stops (removing nothing) when it can't verify them. Changes to `config.env` apply on the next start of the service (`Restart-Service colony-print-node`). Uninstalling keeps the configuration and the logs.

### Self-Update

Every time the service starts, the node updates colony-print and npcolony to their newest versions in PyPI (`pip install --upgrade`), only installing their wheels (nothing is compiled in the node) and skipping the versions that don't support its Python (`Requires-Python`). Their dependencies are only updated when required. pip ignores its configuration files (e.g. `C:\ProgramData\pip\pip.ini`, which any user may create), but may be configured with `PIP_*` values in `config.env` (e.g. `PIP_PROXY`). A failed update (e.g. without internet access) only logs a warning and never prevents the node from running, as it keeps the installed packages, and the service runs the boot script from a copy outside of the packages (`C:\Program Files\Colony Print Node\boot.py`), so a broken or interrupted update never prevents it from starting.

The update is configured in `config.env`:

| Configuration           | Notes                                                                                             |
| ----------------------- | ------------------------------------------------------------------------------------------------- |
| `NODE_UPDATE`           | `0` disables the update.                                                                          |
| `NODE_VERSION`          | Version of colony-print, an exact version (e.g. `0.21.0`) or a specifier (e.g. `<0.22`, `==0.21.*`). |
| `NODE_NPCOLONY_VERSION` | Version of npcolony, as `NODE_VERSION`.                                                           |
| `NODE_INDEX_URL`        | URL of the package index to use instead of PyPI (e.g. a private mirror).                          |

The versions pin a node (or roll it back), as the node installs the newest version they allow, including an older one.

The update may also be requested from the admin, together with the restart of the node and its auto-update (see [Node Control](#node-control)). The auto-update set from the admin is kept in the `state.env` file (next to `config.env`) and takes precedence over `NODE_UPDATE`, and a requested update runs even with the auto-update disabled. The nodes installed by an older installer (0.23.0 or older) keep their boot script, which the self-update doesn't replace, so they're restarted but not updated from the admin until the installer is run again. Their restart still updates them when the auto-update is enabled, as their boot runs it at every start.

### Windows XP

Windows XP (SP3) nodes are installed with a second installer (`colony-print-node-setup-xp-<version>.exe`), which runs on every version of Windows from Windows XP SP3 on (32 and 64 bit). It's used, configured and updated as the other one (same parameters, service, `config.env` and self-update), with the following differences:

* It installs a 32 bit Python 2.7.18 (the last one that runs on Windows XP), together with the Visual C++ 2008 runtime that it requires (Microsoft's redistributable), and requires npcolony 1.7.0 or newer (the first one with wheels for it). The node only updates itself while colony-print, npcolony and their dependencies keep publishing wheels for Python 2.7.
* The service is run by [NSSM](https://nssm.cc) instead of WinSW, which requires a .NET Framework that Windows XP lacks. The log files are rotated when they reach 10 MB, but the rotated ones are never removed.
* NSSM is not detected by the node, so the installer tells the node about it (`NODE_SERVICE=nssm` in the environment of the service), for the node to restart by exiting when restarted from the admin, as it does under WinSW, unless `NODE_RESTART` says otherwise in `config.env` (see [Node Control](#node-control)). The nodes installed by the 0.23.0 installer are not restarted from the admin (they don't advertise it) until they're installed again or have `NODE_RESTART=exit` in their `config.env`.
* The node is installed in the 32 bit program files (`C:\Program Files (x86)\Colony Print Node` on a 64 bit Windows) and, on Windows XP, its configuration and logs are in `C:\Documents and Settings\All Users\Application Data\Colony Print Node`.
* The access to the configuration is restricted as in the other installer, except on the disks without file security (e.g. FAT32), where it's not possible: the installer warns (and asks to continue) that any user of the machine is able to read the secret key and to change the files of the node, which run as the system account. The access is not verified by the installer, as Windows XP has no PowerShell. So the configuration kept by an uninstall is not used by the next install, which must be given the configuration again, only an install over an installed node keeps its configuration.
* Python 2.7 always searches for its modules in the application paths of the registry (the subkeys of `Software\Python\PythonCore\2.7\PythonPath`, e.g. added by pywin32) before its own library, which can't be disabled. The installer warns (and asks to continue) when they exist, as any user able to write in those directories is able to run code as the system account.
* The installer doesn't verify the server URL and the secret key on the versions of Windows older than 8.1 when the server uses HTTPS, as they don't enable its secure protocols (TLS 1.2) by default, which the node itself supports.
* Windows XP has no PDF printer, so one must be installed to use the email mode.

Both installers use the same service, so only one of the nodes is installed in a machine. Installing one of them over the node of the other one (e.g. after upgrading the machine to Windows 10) replaces it, uninstalling the other node and keeping its configuration.

```powershell
.\windows\build.ps1 -XP -Python C:\Python27\python.exe
```

The build requires a 32 bit Python 2.7.18 (with pip, setuptools and wheel) and [Inno Setup 5.6.1](https://files.jrsoftware.org/is/5/), the last one that supports Windows XP. The `Windows Workflow` also builds this installer on every push (the `colony-print-node-windows-xp` artifact), smoke tests it on a Windows runner (not on Windows XP itself) and attaches it to the release. It also installs each of the installers over the node of the other one, to verify that the node is replaced.

## Admin UI

A React-based admin interface is available under `frontends/admin/` for monitoring nodes, jobs and printers.

```bash
cd frontends/admin
npm install
npm run build
```

The built assets are output to `src/colony_print/static/admin-ui/` and served at `/admin-ui` when the server is running.

## Development

To run a localhost development server, use the following commands:

```bash
PORT=8686 \
PYTHONPATH=$BASE_PATH/colony_print/src python \
$BASE_PATH/colony_print/src/colony_print/main.py
```

## License

Colony Print Infra-structure is currently licensed under the [Apache License, Version 2.0](http://www.apache.org/licenses/).

## Build Automation

[![Build Status](https://github.com/hivesolutions/colony-print/workflows/Main%20Workflow/badge.svg)](https://github.com/hivesolutions/colony-print/actions)
[![PyPi Status](https://img.shields.io/pypi/v/colony-print.svg)](https://pypi.python.org/pypi/colony-print)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://www.apache.org/licenses/)
