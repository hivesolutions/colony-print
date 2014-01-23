#!/usr/bin/python
# -*- coding: utf-8 -*-

import appier

import colony_print

EXAMPLE = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\
    <printing_document name=\"hello_world\" font=\"Calibri\" font_size=\"9\">\
        <paragraph text_align=\"center\">\
            <line><text>01-Lugar da Jóia Porto</text></line>\
        </paragraph>\
    </printing_document>"

class BaseController(appier.Controller):

    @appier.controller("BaseController")
    def __init__(self, owner, *args, **kwargs):
        appier.Controller.__init__(self, owner, *args, **kwargs)
        self.manager = None

    @appier.route("/print/example", "POST")
    def print_example(self):
        manager = self.get_manager()

        data = EXAMPLE
        options = dict(name = "pdf")

        return manager.print_language(data, options)

    @appier.route("/print/win32", "POST")
    def print_win32(self):
        return self.template(
            "account/new.html.tpl",
            account = {},
            errors = {}
        )

    def get_manager(self):
        if self.manager: return self.manager
        self.manager = colony_print.PrintingManager()
        self.manager.load()
