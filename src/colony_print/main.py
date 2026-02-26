#!/usr/bin/python
# -*- coding: utf-8 -*-

import appier
import appier_extras


class ColonyPrintApp(appier.APIApp):
    def __init__(self, *args, **kwargs):
        appier.APIApp.__init__(
            self, name="colony-print", parts=(appier_extras.AdminPart,), *args, **kwargs
        )
        self.nodes = dict()
        self.jobs = dict()
        self.jobs_info = appier.LimitedSizeDict(
            max_size=appier.conf("JOB_SIZE", 128, cast=int)
        )

    def _version(self):
        return "0.7.0"

    def _description(self):
        return "Colony Print"

    def _observations(self):
        return "Printing in the cloud"


if __name__ == "__main__":
    app = ColonyPrintApp()
    app.serve()
else:
    __path__ = []
