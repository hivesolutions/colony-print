#!/usr/bin/python
# -*- coding: utf-8 -*-

import appier

class NodeController(appier.Controller):

    @appier.route("/nodes", "GET", json = True)
    def list(self):
        return []

    @appier.route("/nodes/<str:id>", "GET", json = True)
    def show(self, id, printer):
        pass

    @appier.route("/nodes/<str:id>/register", "POST", json = True)
    def register(self, id):
        pass

    @appier.route("/nodes/<str:id>/jobs", "GET", json = True)
    def jobs(self, id):
        pass

    @appier.route("/nodes/<str:id>/printers/<str:printer>/print", ("GET", "POST"), json = True)
    def print_document(self, id, printer):
        #@todo must enqueu the document for printing
        #data_b64 = self.field("data_b64")
        #self.npcolony.print_printer_base64(printer, data_b64)
        pass
