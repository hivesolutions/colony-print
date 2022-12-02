#!/usr/bin/python
# -*- coding: utf-8 -*-

import appier
import appier_extras

class ColonyPrintApp(appier.APIApp):

    def __init__(self, *args, **kwargs):
        appier.APIApp.__init__(
            self,
            name = "colony-print",
            parts = (
                appier_extras.AdminPart,
            ),
            *args, **kwargs
        )
        self.nodes = dict()
        self.jobs = dict()

if __name__ == "__main__":
    app = ColonyPrintApp()
    app.serve()
else:
    __path__ = []
