#!/usr/bin/python
# -*- coding: utf-8 -*-

import appier

class PrinterController(appier.Controller):

    @appier.route("/printers", "GET", json = True)
    @appier.ensure(token = "admin")
    def list(self):
        return self.npcolony.get_devices()

    @appier.route("/printers/hello", "GET", json = True)
    @appier.ensure(token = "admin")
    def hello(self):
        self.npcolony.print_hello()

    @appier.route("/printers/print", "GET", json = True)
    @appier.ensure(token = "admin")
    def print_document_f(self):
        printer = self.field("printer")
        return self.print_document(printer)

    @appier.route("/printers/<str:printer>/print", ("GET", "POST"), json = True)
    @appier.ensure(token = "admin")
    def print_document(self, printer):
        data_b64 = self.field("data_b64")
        self.npcolony.print_printer_base64(printer, data_b64)

    @property
    def npcolony(self):
        import npcolony
        return npcolony
