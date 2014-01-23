# Colony Print Infra-structure

Small web app for the printing of colony based documents.

## Installation

### Pre-requisites

```bash
apt-get install gcc
apt-get install python-dev

pip install appier
pip install netius
pip install pillow
pip install reportlab
```

### Fonts

To be able to use new fonts (other than the ones provided by the system) one must install them
into the `/usr/share/fonts/truetype` directory so they are exposed and ready to
be used by the PDF generation infra-structure. For example calibri is one type of font that should
be exported to an UNIX machine as it is used by mani colony generated documents.

## Running

    ENCODING=gzip PORT=8686 PYTHONPATH=$BASE_PATH/colony_print/src python $BASE_PATH/colony_print/src/colony_print/main.py 
