#!/usr/bin/python
# -*- coding: utf-8 -*-

import appier

class ColonyPrintApp(appier.APIApp):

    def __init__(self, *args, **kwargs):
        appier.APIApp.__init__(
            self,
            name = "colony_print",
            service = True,
            *args, **kwargs
        )
        self.nodes = dict()
        self.jobs = dict()

if __name__ == "__main__":
    app = ColonyPrintApp()
    app.serve()
