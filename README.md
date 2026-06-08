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
The `gravo` engine receives its fonts on a per print job basis through the `extra_fonts` field of the gravo print payload (see [Gravo Print Payload](#gravo-print-payload)) and stages them on a per job temporary directory, so the two flows are independent and operators should not confuse them.

### Engines

There are currently three engines available for printing in Colony Print:

* `npcolony` - The [Colony NPAPI](https://github.com/hivesolutions/colony-npapi) engine, which is used for GDI printing on Windows and CUPS printing on Linux.
* `gravo` - Which allows engraving of text and signatures using [Gravo Pilot](https://github.com/hivesolutions/gravo-pilot). Accepts an `extra_fonts` mapping in the print payload to ship `.f3s` font payloads to the engraving software on a per print job basis (see [Gravo Print Payload](#gravo-print-payload)).
* `text` - A simple virtual printer text engine that prints text to a simple plain text file and returns the file.

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
| `debug`       | boolean         | no       | When `true` the response includes the captured gravo pilot logs. Defaults to `false`.                                                                                                                                                       |
| `extra_fonts` | object          | no       | Mapping of font name to the base64 encoded `.f3s` payload that should be installed for the duration of the engraving session. Each entry is staged on a per job temporary directory and forwarded to gravo pilot's `extra_fonts` parameter. |

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
