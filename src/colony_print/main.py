#!/usr/bin/python
# -*- coding: utf-8 -*-

import appier

import printing

print printing

class ColonyPrintApp(appier.App):

    def __init__(self):
        appier.App.__init__(
            self,
            name = "colony_print",
            service = True
        )

if __name__ == "__main__":
    app = ColonyPrintApp()
    app.serve()
