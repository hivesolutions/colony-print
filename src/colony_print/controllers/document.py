#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
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
        self.font_cache = None

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
        has_size = width > 0.0 and height > 0.0

        mime = self.get_mime(format, b64=b64)
        manager = self.get_manager()

        data = data
        file = appier.legacy.BytesIO()
        options = dict(name=format, file=file)
        if has_size:
            options["size"] = (width, height)
        if format == "pdf":
            options["font_files"] = self.get_font_files(data)

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

    def get_font_files(self, data):
        """
        Installs the fonts declared by the provided XMPL document in the
        font cache of the server, returning the files of the fonts of the
        cache to be used in the conversion of the document.

        As the fonts of the cache never expire (and may be downloaded) the
        documents that declare fonts require the admin token.

        :type data: String
        :param data: The XMPL document to install the fonts.
        :rtype: Dictionary
        :return: The map associating the (lower cased) name and the style
        of the fonts of the cache with the path to their files.
        """

        import colony_print

        fonts = colony_print.xmpl_fonts(data)
        appier.verify(
            not fonts or appier.check_login(self, token="admin"),
            message="Documents declaring fonts require the admin token",
            code=403,
        )
        font_cache = self.get_font_cache()
        for font in fonts:
            font_cache.install(font)
        return font_cache.files()

    def get_font_cache(self):
        import colony_print

        if self.font_cache:
            return self.font_cache
        data_path = appier.conf("DATA_PATH", "./data")
        fonts_path = appier.conf("FONTS_PATH", os.path.join(data_path, "fonts"))
        font_max_size = appier.conf(
            "FONT_MAX_SIZE", colony_print.FONT_MAX_SIZE, cast=int
        )
        self.font_cache = colony_print.FontCache(fonts_path, max_size=font_max_size)
        try:
            self.font_cache.load()
        except Exception as exception:
            self.owner.logger.warning(
                "Problem loading font cache '%s': %s" % (fonts_path, str(exception))
            )
        return self.font_cache
