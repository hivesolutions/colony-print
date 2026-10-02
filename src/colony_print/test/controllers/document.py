#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import re
import base64
import shutil
import logging
import tempfile
import unittest

import appier

import colony_print

FONTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..", "assets", "fonts"
)
""" The path to the directory that contains the fonts bundled
with the repository, used by the documents of the tests """

XMPL = '<?xml version="1.0" encoding="UTF-8"?>\
    <printing_document name="hello_world" font="Colonia" font_size="9">\
        %s\
        <paragraph text_align="center">\
            <line><text>Hello World</text></line>\
        </paragraph>\
    </printing_document>'
""" The template of the hello world XMPL document using the Colonia
font, with its font elements (declarations) """


def build_font(name="Colonia"):
    """
    Builds a true type font file from the Calibri font bundled with the
    repository, renaming its family into the provided name, so that the
    font is not installed in the system.

    :type name: String
    :param name: The name of the family of the font, with the same
    size of the original name (Calibri), as the names are replaced.
    :rtype: String
    :return: The contents of the built font file.
    """

    with open(os.path.join(FONTS_PATH, "calibri.ttf"), "rb") as file:
        data = file.read()
    data = data.replace(b"Calibri", name.encode("utf-8"))
    return data.replace("Calibri".encode("utf-16-be"), name.encode("utf-16-be"))


class DocumentControllerTest(unittest.TestCase):
    def setUp(self):
        self.app = colony_print.ColonyPrintApp(
            level=logging.ERROR, session_c=appier.MemorySession
        )
        self.font_paths = colony_print.printing.pdf.visitor.FONT_PATHS
        colony_print.printing.pdf.visitor.FONT_PATHS = (os.path.join(FONTS_PATH, ""),)
        self.target_dir = tempfile.mkdtemp(prefix="colony-print-document-test-")
        appier.conf_s("FONTS_PATH", self.target_dir)
        session = self.app.session_c.new()
        session["username"] = "admin"
        session["tokens"] = ["admin"]
        self.headers = [("X-Session-Id", session.sid)]

    def tearDown(self):
        colony_print.printing.pdf.visitor.FONT_PATHS = self.font_paths
        appier.conf_r("FONTS_PATH")
        shutil.rmtree(self.target_dir, ignore_errors=True)
        self.app.unload()
        adapter = appier.get_adapter()
        adapter.drop_db()

    def _media_box(self, data):
        pattern = b"/MediaBox \\[ (\\S+) (\\S+) (\\S+) (\\S+) \\]"
        return tuple(float(value) for value in re.search(pattern, data).groups())

    def test_example(self):
        response = self.app.get("/documents/example.binie")
        self.assertEqual(
            response.data,
            b"hello_world\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00@\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00Calibri\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\t\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0c\x00\x00\x00Hello World\x00",
        )
        self.assertEqual(response.headers["Content-Type"], "text/x-binie-base64")

    def test_convert(self):
        response = self.app.post(
            "/documents.binie",
            data=appier.legacy.bytes(colony_print.controllers.document.EXAMPLE),
        )
        self.assertEqual(
            response.data,
            b"hello_world\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01\x00\x00\x00@\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00Calibri\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\t\x00\x00\x00\x03\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x0c\x00\x00\x00Hello World\x00",
        )
        self.assertEqual(response.headers["Content-Type"], "text/x-binie-base64")

    def test_convert_size(self):
        response = self.app.post(
            "/documents.pdf?width=200&height=300",
            data=appier.legacy.bytes(colony_print.controllers.document.EXAMPLE),
        )
        self.assertEqual(response.data[:5], b"%PDF-")
        self.assertEqual(self._media_box(response.data), (0.0, 0.0, 200.0, 300.0))

    def test_convert_width(self):
        response = self.app.post(
            "/documents.pdf?width=200",
            data=appier.legacy.bytes(colony_print.controllers.document.EXAMPLE),
        )
        self.assertEqual(response.data[:5], b"%PDF-")
        self.assertEqual(self._media_box(response.data), (0.0, 0.0, 595.2756, 841.8898))

    def test_convert_fonts(self):
        font = '<font name="Colonia" data_b64="%s"/>' % base64.b64encode(
            build_font()
        ).decode("utf-8")
        data = appier.legacy.bytes(XMPL % font)

        # converting a document that declares fonts requires the admin
        # token, as the fonts are installed in the cache of the server
        response = self.app.post("/documents.pdf", data=data)
        self.assertEqual(response.code, 403)
        self.assertEqual(os.listdir(self.target_dir), [])

        response = self.app.post("/documents.pdf", data=data, headers=self.headers)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.data[:5], b"%PDF-")
        self.assertEqual(b"Colonia" in response.data, True)
        self.assertEqual(len(os.listdir(self.target_dir)), 2)

        # the installed font is used by the documents that don't declare it
        # (without the admin token), as the fonts of the system are
        response = self.app.post("/documents.pdf", data=appier.legacy.bytes(XMPL % ""))
        self.assertEqual(response.code, 200)
        self.assertEqual(b"Colonia" in response.data, True)

        # the declared fonts are ignored when converting to binie (no fonts)
        response = self.app.post("/documents.binie", data=data)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.data[:11], b"hello_world")
        self.assertEqual(b"Colonia\x00" in response.data, True)

        invalid = '<font name="Colonia" url="ftp://fonts.hive.pt/colonia.ttf"/>'
        response = self.app.post(
            "/documents.pdf",
            data=appier.legacy.bytes(XMPL % invalid),
            headers=self.headers,
        )
        self.assertEqual(response.code, 400)

        # the declared font doesn't match the font file (another family)
        invalid = '<font name="Binaria" data_b64="%s"/>' % base64.b64encode(
            build_font()
        ).decode("utf-8")
        response = self.app.post(
            "/documents.pdf",
            data=appier.legacy.bytes(XMPL % invalid),
            headers=self.headers,
        )
        self.assertEqual(response.code, 400)

    def test_get_font_cache(self):
        controller = colony_print.controllers.DocumentController(self.app)
        font_cache = controller.get_font_cache()
        self.assertEqual(font_cache.path, self.target_dir)
        self.assertEqual(font_cache.max_size, colony_print.FONT_MAX_SIZE)
        self.assertEqual(controller.get_font_cache(), font_cache)

        # an index of the font cache that fails to load (eg: corrupted by a
        # power loss) is logged and the documents are converted with an empty
        # cache, where the fonts are installed again
        with open(os.path.join(self.target_dir, "index.json"), "wb") as file:
            file.write(b"\x00" * 64)
        controller = colony_print.controllers.DocumentController(self.app)
        font_cache = controller.get_font_cache()
        self.assertEqual(font_cache.installed(), [])

        font = '<font name="Colonia" data_b64="%s"/>' % base64.b64encode(
            build_font()
        ).decode("utf-8")
        response = self.app.post(
            "/documents.pdf",
            data=appier.legacy.bytes(XMPL % font),
            headers=self.headers,
        )
        self.assertEqual(response.code, 200)
        self.assertEqual(b"Colonia" in response.data, True)
        response = self.app.post("/documents.pdf", data=appier.legacy.bytes(XMPL % ""))
        self.assertEqual(response.code, 200)
        self.assertEqual(b"Colonia" in response.data, True)
