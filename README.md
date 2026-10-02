# [Colony Print Infra-structure](http://colony-print.hive.pt)

Small web app for printing Colony-based documents.

This project includes two main components:

* The Web App end-point that provides XML to Binie conversion `colony_print.controllers`
* The structure conversion infra-structure (Visitors, AST, etc.) `colony_print.printing`

## Features

* Cloud printing, with minimal configuration
* Multiple engine support (npcolony, gravo, text)
* XMPL to Binie conversion
* PDF generation with custom fonts and images
* [GDI](https://en.wikipedia.org/wiki/Graphics_Device_Interface) printing (Windows) via [Colony NPAPI (npcolony)](https://github.com/hivesolutions/colony-npapi)
* [CUPS](https://en.wikipedia.org/wiki/CUPS) printing (Linux) via [Colony NPAPI (npcolony)](https://github.com/hivesolutions/colony-npapi)
* Windows installer for the nodes, which update themselves from the server (see [Windows Node](#windows-node))

## Binie Specification

For a detailed understanding of the Binie file format used in this project, refer to the [Binie File Format Specification](doc/binie.md). This document outlines the structure and organization of the Binie file format, which is essential for developing compatible applications and tools.

## XMPL Specification

The XML Markup Language for Printing (XMPL) is integral to our document processing pipeline. For an in-depth understanding of the XMPL structure and its seamless convertibility to Binie, see the [XMPL File Format Specification](doc/xmpl.md).

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

### Fonts

To be able to use new fonts (other than the ones provided by the system), one must install them into the `/usr/share/fonts/truetype` directory so they are exposed and ready to be used by the PDF generation infra-structure. For example, Calibri is one type of font that should be exported to a UNIX machine as many colony-generated documents use it.

The `/usr/share/fonts/truetype` install path is shared by the PDF generation engine.
Linux (CUPS) nodes need the same fonts to lay out the Binie documents they print. They look for the font files by name in the same paths and, as Windows does, fall back to the closest installed font found through fontconfig (`fc-match`), so installing Calibri (or the metric compatible Carlito font) keeps the layout identical to the Windows one. The same applies to the barcode fonts of the documents (e.g. the `2 of 5` font of the Omni product labels, looked up as `2 of 5.ttf`), whose barcodes are otherwise printed as the letters they are encoded with.
The `gravo` engine receives its fonts on a per print job basis through the `extra_fonts` field of the gravo print payload (see [Gravo Print Payload](#gravo-print-payload)) and stages them on a per job temporary directory, so the two flows are independent and operators should not confuse them.

### Engines

There are currently three engines available for printing in Colony Print:

* `npcolony` - The [Colony NPAPI](https://github.com/hivesolutions/colony-npapi) engine, which is used for GDI printing on Windows and CUPS printing on Linux.
* `gravo` - Which allows engraving of text and signatures using [Gravo Pilot](https://github.com/hivesolutions/gravo-pilot). Accepts an `extra_fonts` mapping in the print payload to ship `.f3s` font payloads to the engraving software on a per print job basis (see [Gravo Print Payload](#gravo-print-payload)).
* `text` - A simple virtual printer text engine that prints text to a simple plain text file and returns the file.

### Print Request

Every engine is reached through the same print endpoint and request envelope. A job is submitted to `/nodes/<id>/print` (or `/nodes/<id>/printers/<printer>/print` to target a specific printer) with the following fields:

| Field      | Type   | Required | Notes                                                                                                      |
| ---------- | ------ | -------- | ---------------------------------------------------------------------------------------------------------- |
| `data`     | string | yes\*    | Raw document data, base64 encoded by the server before dispatch. Mutually exclusive with `data_b64`.       |
| `data_b64` | string | yes\*    | Base64 encoded document data, the engine specific payload described below. Mutually exclusive with `data`. |
| `name`     | string | no       | Human readable job name. Defaults to the generated job identifier.                                         |
| `type`     | string | no       | Target engine: `npcolony` (default), `gravo` or `text`.                                                    |
| `format`   | string | no       | Expected document format (e.g. `binie`, `pdf`). Validated against the node format when provided.           |
| `options`  | object | no       | Extra per job options (see table below). Keys outside the supported set are discarded.                     |

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

### npcolony Print Payload

The `npcolony` engine is the default and prints through [Colony NPAPI](https://github.com/hivesolutions/colony-npapi) using GDI on Windows and CUPS on Linux. Its payload is the binary print document carried in `data_b64`, typically a [Binie](doc/binie.md) document produced by the XMPL to Binie conversion, dispatched directly to the target printer. There are no JSON fields: the printing behaviour is tuned through the options and the optional `format` field described in [Print Request](#print-request).

On Windows the Binie document is drawn directly through GDI. Linux (CUPS) nodes only print PDF documents, so they convert Binie jobs (with the `binie` format, or without a format when the payload is a valid Binie document) into a PDF laid out with the same rules as GDI: the paper size of the document when it defines one and the printer accepts it as a custom paper size (as the Windows driver of the printer does), and the printer's default paper size otherwise (e.g. a label printed on an A4 printer comes out at its real size in the top left corner of the page), with the content laid out from the top left corner of the printable area of the page and printed without scaling. The `media` option doesn't apply to them, as their pages are always laid out for that paper size. PDF documents and any other data are sent to CUPS untouched.

### Linux (CUPS) Printing

The printer of the job (or `NODE_PRINTER` when the job has none) selects the CUPS queue, and `default`, the default value of `NODE_PRINTER`, selects the default queue (or the only queue, when none is the default). Jobs for a queue that does not exist, or that CUPS refuses, fail with an error instead of being reported as printed.

Each queue should use a driver for its printer and a default paper size that matches the loaded paper, as that size is used for the Binie documents that do not define one, or whose size the printer does not accept as a custom paper size (e.g. `lpadmin -p receipt -o PageSize=RP80x297`):

* Receipt printers - the vendor CUPS driver (e.g. the Epson TM series driver), with its paper reduction options enabled to avoid feeding blank paper at the end of the receipt.
* Label printers - the label drivers shipped with CUPS (Zebra, Dymo) or the vendor ones, with the default size set to the loaded label.
* Office printers - driverless (IPP Everywhere) queues.

The custom paper sizes a printer accepts, and their margins, are the ones of the PPD of its queue, as reported by npcolony. With npcolony versions that don't report them, a Binie document only uses its own size when it matches the default paper size of the queue.

In `email` mode the PDF document is written to the output file (print to file) instead of being printed, as it happens with the PDF printer on Windows.

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

## Windows Node

Windows 10 and 11 (64 bit) nodes are installed with a `setup.exe` installer. It installs everything the node needs: an embedded Python, colony-print, [Colony NPAPI (npcolony)](https://github.com/hivesolutions/colony-npapi) for the native (GDI) printing, and their dependencies. The node runs as the `colony-print-node` Windows service, which starts with the machine and updates itself from the server every time it starts.

### Building the Installer

```powershell
.\windows\build.ps1 -Python C:\Python314\python.exe
```

The build requires a 64 bit Python (the embedded Python is the same version), the Visual C++ Build Tools (npcolony is compiled from its sources) and [Inno Setup 6](https://jrsoftware.org/isinfo.php). It creates the installer (`dist\colony-print-node-setup-<version>.exe`) and the packages of the node (`dist\packages\*.whl`), which are uploaded to the server for the self-update. The `Windows Workflow` builds both on every push (the `colony-print-node-windows` artifact) and smoke tests the installer on a Windows runner. When a release is published, it also attaches the installer to the release, for which the tag of the release must match the version in `setup.py` (e.g. `0.21.0`). A failed attach can be retried by running the workflow manually with the tag of the release.

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

The node is installed in `C:\Program Files\Colony Print Node`. Its configuration (`config.env`), logs and downloaded packages are in `C:\ProgramData\Colony Print Node`, which only the system account and the administrators can access, as it holds the secret key. A data directory (or configuration) owned by, or accessible to, any other user (e.g. created by a user before the install) is never used, the installer removes it and creates the data directory already restricted. The installer verifies the owner and the access with PowerShell when the service isn't installed, and stops (removing nothing) when it can't verify them. Changes to `config.env` apply on the next start of the service (`Restart-Service colony-print-node`). Uninstalling keeps the configuration and the logs.

### Self-Update

Every time the service starts, the node lists the packages hosted by the server and downloads the ones compatible with it. It then installs the newest version of each package it has installed (and of colony-print and npcolony) when that version differs from the installed one, skipping the versions that don't support its Python (`Requires-Python`). A version is rolled out by uploading its packages and rolled back by removing them from the server. A failed update never prevents the node from running, as it keeps the installed packages, and the service runs the boot script from a copy outside of the packages (`C:\Program Files\Colony Print Node\boot.py`), so a broken or interrupted update never prevents it from starting. Updates may be disabled with `NODE_UPDATE=0` in `config.env`, and the packages may be hosted elsewhere with `PACKAGES_URL` (the secret key is only sent to the server itself, never to other hosts, including the ones of the redirects).

As the packages are installed and run by the service (as the system account), they're only retrieved through HTTPS, or from the local machine (including the redirects), a server reached through plain HTTP is not used for updates (the installer warns about it), unless the insecure update is explicitly allowed with `NODE_UPDATE_INSECURE=1` in `config.env`.

The packages (wheels) are managed with the following endpoints of the server, which require the secret key, and are stored in `PACKAGES_PATH` (`DATA_PATH/packages` by default, which must be persisted, e.g. as a Docker volume). As every node keeps the secret key and runs the packages, uploading and removing them also requires the packages key, set with `PACKAGES_KEY` in the server (publishing is disabled without it) and sent in the `X-Packages-Key` header, which must never be given to the nodes:

| Endpoint                  | Notes                                                                          |
| ------------------------- | ------------------------------------------------------------------------------ |
| `GET /packages`           | Lists the packages, with their name, version, size and SHA256 digest.          |
| `POST /packages`          | Uploads packages, as `file` fields of a multipart request.                     |
| `PUT /packages/<file>`    | Uploads a package, as the body of the request (`application/octet-stream`).    |
| `GET /packages/<file>`    | Downloads a package.                                                           |
| `DELETE /packages/<file>` | Removes a package.                                                             |

To roll out a build, upload its packages and restart the nodes (or wait for their next boot):

```bash
for file in dist/packages/*.whl; do
    curl -H "X-Secret-Key: $SECRET_KEY" -H "X-Packages-Key: $PACKAGES_KEY" -F "file=@$file" $BASE_URL/packages
done
```

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
