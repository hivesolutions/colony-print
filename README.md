# [Colony Print Infra-structure](http://colony-print.hive.pt)

Small web app for printing of Colony based documents.

This project includes two main components:

* The web app end point that allows for XML to Binie conversion `colony_print.controllers`
* The structure conversion infra-structure (visitors, ast, etc.) `colony_print.printing`

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

To be able to use new fonts (other than the ones provided by the system) one must install them
into the `/usr/share/fonts/truetype` directory so they are exposed and ready to
be used by the PDF generation infra-structure. For example calibri is one type of font that should
be exported to an UNIX machine as it is used by mani colony generated documents.

## Running

```bash
PORT=8686 \
PYTHONPATH=$BASE_PATH/colony_print/src python \
$BASE_PATH/colony_print/src/colony_print/main.py
```

## License

Colony Print Infra-structure is currently licensed under the [Apache License, Version 2.0](http://www.apache.org/licenses/).

## Build Automation

[![Build Status](https://app.travis-ci.com/hivesolutions/colony-print.svg?branch=master)](https://travis-ci.com/github/hivesolutions/colony-print)
[![Coverage Status](https://coveralls.io/repos/hivesolutions/colony-print/badge.svg?branch=master)](https://coveralls.io/r/hivesolutions/colony-print?branch=master)
[![PyPi Status](https://img.shields.io/pypi/v/colony-print.svg)](https://pypi.python.org/pypi/colony-print)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://www.apache.org/licenses/)
