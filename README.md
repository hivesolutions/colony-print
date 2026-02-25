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

To be able to use new fonts (other than the ones provided by the system), one must install them
into the `/usr/share/fonts/truetype` directory so they are exposed and ready to
be used by the PDF generation infra-structure. For example, Calibri is one type of font that should
be exported to a UNIX machine as many colony-generated documents use it.

### Engines

There are currently three engines available for printing in Colony Print:

* `npcolony` - The [Colony NPAPI](https://github.com/hivesolutions/colony-npapi) engine, which is used for GDI printing on Windows and CUPS printing on Linux.
* `gravo` - Which allows engraving of text and signatures using [Gravo Pilot](https://github.com/hivesolutions/gravo-pilot).
* `text` - A simple virtual printer text engine that prints text to a simple plain text file and returns the file.

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
