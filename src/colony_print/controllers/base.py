#!/usr/bin/python
# -*- coding: utf-8 -*-

import cStringIO

import appier

import colony_print

MIME = dict(
    binie = "text/x-binie",
    pdf = "application/pdf"
)

EXAMPLE = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\
    <printing_document name=\"hello_world\" font=\"Calibri\" font_size=\"9\">\
        <paragraph text_align=\"center\">\
            <line><text>Hello World</text></line>\
        </paragraph>\
    </printing_document>"

class BaseController(appier.Controller):

    @appier.controller("BaseController")
    def __init__(self, owner, *args, **kwargs):
        appier.Controller.__init__(self, owner, *args, **kwargs)
        self.manager = None

    @appier.route("/print/example.<format>", "GET")
    def print_example(self, format):
        return self.send_print(EXAMPLE, format)

    @appier.route("/print.<format>", "POST")
    def print_language(self, format):
        # data = @todo: tenho de sacar os dados de post
        return self.send_print(EXAMPLE, format)

    def send_print(self, data, format):
        mime = self.get_mime(format)
        manager = self.get_manager()

        data = data
        file = cStringIO.StringIO()
        options = dict(name = format, file = file)

        manager.print_language(data, options)
        value = file.getvalue()

        self.content_type(mime)
        return value

    def get_mime(self, format):
        return MIME.get(format, "application/octet-stream")

    def get_manager(self):
        if self.manager: return self.manager
        self.manager = colony_print.PrintingManager()
        self.manager.load()
        return self.manager
