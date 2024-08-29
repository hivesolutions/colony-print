#!/usr/bin/python
# -*- coding: utf-8 -*-

import base64

import appier

MIME = dict(binie="text/x-binie", pdf="application/pdf")
""" Map defining the association between the print
format naming and the associated base mime type value
(note that this value may be complemented with base64) """

EXAMPLE = '<?xml version="1.0" encoding="UTF-8"?>\
    <printing_document name="hello_world" font="Calibri" font_size="9">\
        <paragraph text_align="center">\
            <line><text>Hello World</text></line>\
        </paragraph>\
    </printing_document>'
""" Example XML string that should display an hello world
message using the XML printing language (XMPL) """


class DocumentController(appier.Controller):
    def __init__(self, owner, *args, **kwargs):
        appier.Controller.__init__(self, owner, *args, **kwargs)
        self.manager = None

    @appier.route("/documents/example.<format>", "GET")
    def example(self, format):
        return self.send_print(EXAMPLE, format)

    @appier.route("/documents.<format>", "POST")
    def convert(self, format):
        # retrieves the current request reference and then
        # uses it to retrieve its "raw" data, which should
        # contain the XML string (XMPL) for the generation of the
        # of binie result and then sends the value for print
        request = self.get_request()
        data = request.get_data()
        return self.send_print(data, format=format)

    def send_print(self, data, format="binie"):
        """
        Converts ("prints") the provided data (XMPL) into the target
        format, either Binie or PDF, and then sends the converted
        data back to the client.

        This method is expected to be running inside an Appier request
        handling context, as it sets content type and other headers.

        :type data: String
        :param data: The data to be converted into the target format.
        :type format: String
        :param format: The target format to be used for the conversion.
        :rtype: String
        :return: The converted data in the target format.
        :see: https://github.com/hivesolutions/colony-print/blob/master/doc/xmpl.md
        :see: https://github.com/hivesolutions/colony-print/blob/master/doc/binie.md
        """

        # retrieves the various optional fields for printing
        # and then parses them creating the composite values
        # (should include the size tuple)
        b64 = self.field("base64", False, cast=bool)
        width = self.field("width", 0.0, cast=float)
        height = self.field("height", 0.0, cast=float)
        has_size = width > 0.0 and width > 0.0

        mime = self.get_mime(format, b64=base64)
        manager = self.get_manager()

        data = data
        file = appier.legacy.BytesIO()
        options = dict(name=format, file=file)
        if has_size:
            options["size"] = (width, height)

        manager.print_language(data, options)
        value = file.getvalue()
        value = base64.b64encode(value) if b64 else value

        self.content_type(mime)
        return value

    def get_mime(self, format, b64=False):
        mime = MIME.get(format, "application/octet-stream")
        mime = mime + "-base64" if b64 else mime
        return mime

    def get_manager(self):
        import colony_print

        if self.manager:
            return self.manager
        self.manager = colony_print.PrintingManager()
        self.manager.load()
        return self.manager
