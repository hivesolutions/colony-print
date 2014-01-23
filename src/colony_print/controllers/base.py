#!/usr/bin/python
# -*- coding: utf-8 -*-

import base64
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
        base64 = self.get_field("base64", False)
        data = self.request.data
        return self.send_print(data, format, b64 = base64)

    def send_print(self, data, format, b64 = False):
        mime = self.get_mime(format, b64 = base64)
        manager = self.get_manager()

        data = data
        file = cStringIO.StringIO()
        options = dict(name = format, file = file)

        manager.print_language(data, options)
        value = file.getvalue()
        value = base64.b64encode(value) if b64 else value

        self.content_type(mime)
        return value

    def get_mime(self, format, b64 = False):
        mime = MIME.get(format, "application/octet-stream")
        mime = mime + "-base64" if b64 else mime
        return mime

    def get_manager(self):
        if self.manager: return self.manager
        self.manager = colony_print.PrintingManager()
        self.manager.load()
        return self.manager
