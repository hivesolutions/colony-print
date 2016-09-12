#!/usr/bin/python
# -*- coding: utf-8 -*-

import appier

class PrinterController(appier.Controller):

    @appier.route("/printers.json", "GET")
    def list(self):
        return []

    @appier.route("/printers/<str:id>/print.json", "POST")
    def print_document(self, format):
        return []
