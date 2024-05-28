#!/usr/bin/python
# -*- coding: utf-8 -*-

from . import main

if __name__ == "__main__":
    app = main.ColonyPrintApp()
    app.serve()
else:
    __path__ = []
