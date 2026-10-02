#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import re
import zlib
import struct
import shutil
import tempfile
import unittest

import appier

import PIL.Image

import reportlab.pdfbase.pdfmetrics

import colony_print

FONTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..", "assets", "fonts"
)
""" The path to the directory that contains the fonts bundled
with the repository, used by the documents of the tests """

RECEIPT_SIZE = (226.77, 841.89)
""" The size (in points) of the 80 mm (roll) receipt media """

RECEIPT_MARGINS = (11.34, 0.0, 11.34, 0.0)
""" The margins (in points) of a typical 80 mm receipt printer,
resulting in a printable area that is 72 mm wide """

PRINTABLE_WIDTH = 4081
""" The width (in twips) of the printable area of the 80 mm
receipt printer, as calculated by windows (truncated) """

CALIBRI_EM = 9 * 2048 / 2500.0
""" The size of the (em of the) Calibri font for which the height
of its (windows) cell is 9 points, as its ascent plus descent is
2500 units (1950 + 550) for 2048 units per em """

CALIBRI_ASCENT = 9 * 1950 / 2500.0
""" The ascent (distance from the top of the cell to the baseline)
of the Calibri font for a cell height of 9 points """

EXAMPLE = '<?xml version="1.0" encoding="UTF-8"?>\
    <printing_document name="hello_world" font="Calibri" font_size="9">\
        <paragraph text_align="center">\
            <line><text>Hello World</text></line>\
        </paragraph>\
    </printing_document>'
""" Example XML string that should display an hello world
message using the XML printing language """

EXAMPLE_FONT = '<?xml version="1.0" encoding="UTF-8"?>\
    <printing_document name="hello_world" font="Colonia" font_size="9">\
        <paragraph text_align="center">\
            <line><text>Hello World</text></line>\
            <line font_style="bold"><text>Hello World</text></line>\
        </paragraph>\
    </printing_document>'
""" Example XML string that should display an hello world
message using the Colonia font (in its regular and bold styles)
using the XML printing language """

EXAMPLE_STYLE = '<?xml version="1.0" encoding="UTF-8"?>\
    <printing_document name="hello_world" font="Calibri" font_size="9">\
        <paragraph text_align="center">\
            <line><text>Hello World</text></line>\
            <line font_style="bold"><text>Hello World</text></line>\
        </paragraph>\
    </printing_document>'
""" Example XML string that should display an hello world
message using the Calibri font (in its regular and bold styles)
using the XML printing language """


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


class VisitorTest(unittest.TestCase):
    def setUp(self):
        self.font_paths = colony_print.printing.pdf.visitor.FONT_PATHS
        colony_print.printing.pdf.visitor.FONT_PATHS = (os.path.join(FONTS_PATH, ""),)
        self.manager = colony_print.PrintingManager()
        self.manager.load()
        self.target_dir = tempfile.mkdtemp(prefix="colony-print-visitor-test-")

    def tearDown(self):
        colony_print.printing.pdf.visitor.FONT_PATHS = self.font_paths
        self.manager.unload()
        shutil.rmtree(self.target_dir, ignore_errors=True)

    def test_print_language(self):
        file = appier.legacy.BytesIO()
        options = dict(name="pdf", file=file)
        self.manager.print_language(EXAMPLE, options)
        result = file.getvalue()
        self.assertEqual(result[:5], b"%PDF-")
        self.assertEqual(b"FlateDecode" in result, True)
        self.assertEqual(b"ASCII85Decode" in result, False)

    def test_print_language_fonts(self):
        file_path = os.path.join(self.target_dir, "colonia.ttf")
        with open(file_path, "wb") as file:
            file.write(build_font())

        # the font of the document is only installed on demand, so it
        # may not be printed without the file of the installed font
        file = appier.legacy.BytesIO()
        options = dict(name="pdf", file=file)
        self.assertRaises(
            colony_print.InvalidFont,
            lambda: self.manager.print_language(EXAMPLE_FONT, options),
        )

        # prints the document with the installed font (in its regular
        # style), that is also used for the bold style of the document
        file = appier.legacy.BytesIO()
        options = dict(
            name="pdf", file=file, font_files={("colonia", "regular"): file_path}
        )
        self.manager.print_language(EXAMPLE_FONT, options)
        result = file.getvalue()
        self.assertEqual(result[:5], b"%PDF-")
        self.assertEqual(b"Colonia" in result, True)

        # the other fonts are not affected by the installed fonts
        file = appier.legacy.BytesIO()
        options = dict(
            name="pdf", file=file, font_files={("colonia", "regular"): file_path}
        )
        self.manager.print_language(EXAMPLE, options)
        self.assertEqual(b"Colonia" in file.getvalue(), False)

        # another file of the font (eg: a newer version) is the one used
        # by the next documents, replacing the one registered before
        updated_path = os.path.join(self.target_dir, "colonia-updated.ttf")
        with open(updated_path, "wb") as file:
            file.write(build_font() + b"\0")
        file = appier.legacy.BytesIO()
        options = dict(
            name="pdf", file=file, font_files={("colonia", "regular"): updated_path}
        )
        self.manager.print_language(EXAMPLE_FONT, options)
        font = reportlab.pdfbase.pdfmetrics.getFont("Colonia")
        self.assertEqual(font.face.filename, updated_path)

    def test_print_language_fonts_style(self):
        # the font of the system with the exact style (bold) is used before
        # the other style of the font installed on demand, as windows does
        file_path = os.path.join(self.target_dir, "calibri.ttf")
        shutil.copyfile(os.path.join(FONTS_PATH, "calibri.ttf"), file_path)
        file = appier.legacy.BytesIO()
        options = dict(
            name="pdf", file=file, font_files={("calibri", "regular"): file_path}
        )
        self.manager.print_language(EXAMPLE_STYLE, options)
        self.assertEqual(file.getvalue()[:5], b"%PDF-")
        bold = reportlab.pdfbase.pdfmetrics.getFont("Calibrib")
        self.assertEqual(os.path.basename(bold.face.filename), "calibrib.ttf")
        regular = reportlab.pdfbase.pdfmetrics.getFont("Calibri")
        self.assertEqual(regular.face.filename, file_path)


class BinieRendererTest(unittest.TestCase):
    def setUp(self):
        self.font_paths = colony_print.printing.pdf.visitor.FONT_PATHS
        colony_print.printing.pdf.visitor.FONT_PATHS = (os.path.join(FONTS_PATH, ""),)
        self.target_dir = tempfile.mkdtemp(prefix="colony-print-renderer-test-")

    def tearDown(self):
        colony_print.printing.pdf.visitor.FONT_PATHS = self.font_paths
        shutil.rmtree(self.target_dir, ignore_errors=True)

    def _binie(self, elements, title=b"test", width=0, height=0):
        data = struct.pack("<256sIII", title, width, height, len(elements))
        for element_type, element in elements:
            data += struct.pack("<II", element_type, len(element)) + element
        return data

    def _text(
        self,
        text,
        y=0,
        font=b"Calibri",
        font_size=9,
        text_align=1,
        text_weight=0,
        text_italic=0,
        margin_left=0,
        margin_right=0,
        position_x=0,
        position_y=0,
        block_width=0,
        block_height=0,
    ):
        text_encoded = text.encode("utf-8")
        element = struct.pack(
            "<ii256sIIIIIIIIIII",
            0,
            y,
            font,
            font_size,
            text_align,
            text_weight,
            text_italic,
            margin_left,
            margin_right,
            position_x,
            position_y,
            block_width,
            block_height,
            len(text_encoded) + 1,
        )
        return (1, element + text_encoded + b"\0")

    def _image(
        self,
        size=(20, 10),
        y=0,
        text_align=1,
        position_x=0,
        position_y=0,
        block_width=0,
        block_height=0,
    ):
        buffer = appier.legacy.BytesIO()
        PIL.Image.new("RGB", size, color="white").save(buffer, "bmp")
        image = buffer.getvalue()
        element = struct.pack(
            "<iiIIIIII",
            0,
            y,
            text_align,
            position_x,
            position_y,
            block_width,
            block_height,
            len(image),
        )
        return (2, element + image)

    def _render(self, data, size=RECEIPT_SIZE, margins=RECEIPT_MARGINS):
        renderer = colony_print.BinieRenderer(size=size, margins=margins)
        file = appier.legacy.BytesIO()
        renderer.render(data, file)
        return renderer, file.getvalue()

    def _pages(self, data):
        # extracts the (decompressed) content streams of the pages from
        # the PDF document, the ones that contain drawing operations
        pages = []
        for match in re.finditer(b"<<([^>]*?)>>\\s*stream\\r?\\n", data):
            if not b"FlateDecode" in match.group(1):
                continue
            end = data.index(b"endstream", match.end())
            try:
                content = zlib.decompress(data[match.end() : end])
            except Exception:
                continue
            if not b" Tf " in content:
                continue
            pages.append(content)
        return pages

    def _texts(self, content):
        pattern = (
            b"BT 1 0 0 1 (\\S+) (\\S+) Tm /(\\S+) (\\S+) Tf \\S+ TL \\((.*?)\\) Tj"
        )
        return [
            (float(x), float(y), font, float(size), text)
            for x, y, font, size, text in re.findall(pattern, content)
        ]

    def _rects(self, content):
        pattern = b"n (\\S+) (\\S+) (\\S+) (\\S+) re f\\*"
        return [
            tuple(float(value) for value in rect)
            for rect in re.findall(pattern, content)
        ]

    def _images(self, content):
        pattern = b"q\\s+(\\S+) 0 0 (\\S+) (\\S+) (\\S+) cm\\s+/\\S+ Do\\s+Q"
        return [
            tuple(float(value) for value in image)
            for image in re.findall(pattern, content)
        ]

    def _media_box(self, data):
        pattern = b"/MediaBox \\[ (\\S+) (\\S+) (\\S+) (\\S+) \\]"
        return tuple(float(value) for value in re.search(pattern, data).groups())

    def test_init(self):
        renderer = colony_print.BinieRenderer()
        self.assertEqual(renderer.size, colony_print.printing.pdf.visitor.PAPER_SIZE)
        self.assertEqual(renderer.margins, (0.0, 0.0, 0.0, 0.0))
        self.assertEqual(renderer.custom, True)
        self.assertEqual(renderer.font_files, {})
        self.assertEqual(renderer.fonts, {})

        font_files = {("colonia", "regular"): "/fonts/colonia.ttf"}
        renderer = colony_print.BinieRenderer(
            size=RECEIPT_SIZE,
            margins=RECEIPT_MARGINS,
            custom=False,
            font_files=font_files,
        )
        self.assertEqual(renderer.size, RECEIPT_SIZE)
        self.assertEqual(renderer.margins, RECEIPT_MARGINS)
        self.assertEqual(renderer.custom, False)
        self.assertEqual(renderer.font_files, font_files)

    def test_render(self):
        data = self._binie([self._text("Hello World")], title=b"hello_world")
        renderer, result = self._render(data)
        self.assertEqual(result[:5], b"%PDF-")
        self.assertEqual(b"ASCII85Decode" in result, False)
        self.assertEqual(b"/Title (hello_world)" in result, True)
        self.assertEqual(self._media_box(result), (0.0, 0.0) + RECEIPT_SIZE)
        self.assertEqual(renderer.origin, (11.34, 841.89))
        self.assertEqual(renderer.clip_box, (0, 0, PRINTABLE_WIDTH, -16837))
        self.assertEqual(renderer.vertical_size, 297)
        self.assertEqual(len(self._pages(result)), 1)

    def test_render_document_size(self):
        data = self._binie([self._text("Hello World")], width=800, height=1000)
        renderer, result = self._render(data)
        width, height = self._media_box(result)[2:]
        self.assertAlmostEqual(width, 226.77, places=2)
        self.assertAlmostEqual(height, 283.46, places=2)
        self.assertAlmostEqual(renderer.origin[0], 11.34, places=2)
        self.assertAlmostEqual(renderer.origin[1], 283.46, places=2)
        self.assertEqual(renderer.vertical_size, 100)

        x, y, _font, _size, _text = self._texts(self._pages(result)[0])[0]
        self.assertAlmostEqual(x, 11.34, places=2)
        self.assertAlmostEqual(y, 283.46 - CALIBRI_ASCENT, places=2)

    def test_render_document_size_ignored(self):
        data = self._binie([self._text("Hello World")], width=800, height=80)
        renderer = colony_print.BinieRenderer(
            size=(595.28, 841.89), margins=(12.0, 12.0, 12.0, 12.0), custom=False
        )
        file = appier.legacy.BytesIO()
        renderer.render(data, file)
        result = file.getvalue()
        self.assertEqual(self._media_box(result), (0.0, 0.0, 595.28, 841.89))
        self.assertEqual(renderer.origin, (12.0, 829.89))
        self.assertEqual(renderer.vertical_size, 288)
        self.assertEqual(len(self._pages(result)), 1)

        x, y, _font, _size, _text = self._texts(self._pages(result)[0])[0]
        self.assertAlmostEqual(x, 12.0, places=2)
        self.assertAlmostEqual(y, 829.89 - CALIBRI_ASCENT, places=2)

    def test_render_rounded_size(self):
        data = self._binie(
            [self._text("Top"), self._text("Bottom", y=-5461)], width=800, height=1000
        )
        renderer = colony_print.BinieRenderer(
            size=(226.77, 283.46), margins=(0.0, 0.0, 0.0, 0.0), custom=False
        )
        file = appier.legacy.BytesIO()
        renderer.render(data, file)
        result = file.getvalue()
        self.assertEqual(renderer.vertical_size, 100)
        self.assertEqual(len(self._pages(result)), 1)

        renderer = colony_print.BinieRenderer(
            size=(226.77, 283.0), margins=(0.0, 0.0, 0.0, 0.0), custom=False
        )
        file = appier.legacy.BytesIO()
        renderer.render(data, file)
        result = file.getvalue()
        self.assertEqual(renderer.vertical_size, 100)
        self.assertEqual(len(self._pages(result)), 1)

        renderer = colony_print.BinieRenderer(
            size=(226.77, 282.9), margins=(0.0, 0.0, 0.0, 0.0), custom=False
        )
        file = appier.legacy.BytesIO()
        renderer.render(data, file)
        result = file.getvalue()
        self.assertEqual(renderer.vertical_size, 99)
        self.assertEqual(len(self._pages(result)), 2)

        data = self._binie(
            [self._text("Top"), self._text("Bottom", y=-16629)],
            width=2100,
            height=2970,
        )
        renderer, result = self._render(data, margins=(0.0, 0.0, 0.0, 0.0))
        self.assertEqual(renderer.vertical_size, 297)
        self.assertEqual(len(self._pages(result)), 1)

    def test_render_default_size(self):
        data = self._binie([self._text("Hello World")])
        renderer = colony_print.BinieRenderer()
        file = appier.legacy.BytesIO()
        renderer.render(data, file)
        width, height = self._media_box(file.getvalue())[2:]
        self.assertAlmostEqual(width, 595.28, places=2)
        self.assertAlmostEqual(height, 841.89, places=2)
        self.assertEqual(renderer.origin[0], 0.0)

    def test_render_unknown_element(self):
        data = self._binie([(3, b"\0" * 16), self._text("Hello World")])
        _renderer, result = self._render(data)
        texts = self._texts(self._pages(result)[0])
        self.assertEqual(len(texts), 1)
        self.assertEqual(texts[0][4], b"Hello World")

    def test_render_invalid(self):
        data = self._binie([self._text("Hello World")])
        self.assertRaises(colony_print.InvalidBinie, lambda: self._render(data[:-1]))
        self.assertRaises(
            colony_print.InvalidBinie, lambda: self._render(b"%PDF-1.4 document")
        )

    def test_render_text(self):
        data = self._binie([self._text("Hello World")])
        renderer, result = self._render(data)
        content = self._pages(result)[0]

        x, y, _font, size, text = self._texts(content)[0]
        self.assertEqual(text, b"Hello World")
        self.assertAlmostEqual(x, 11.34, places=2)
        self.assertAlmostEqual(y, 841.89 - CALIBRI_ASCENT, places=2)
        self.assertAlmostEqual(size, CALIBRI_EM, places=4)

        rect_x, rect_y, rect_width, rect_height = self._rects(content)[0]
        self.assertAlmostEqual(rect_x, 11.34, places=2)
        self.assertAlmostEqual(rect_y, 841.89 - 9, places=2)
        self.assertEqual(rect_height, 9.0)
        self.assertEqual(rect_width > 30.0 and rect_width < 60.0, True)
        self.assertEqual(list(renderer.fonts.keys()), [("Calibri", "regular")])

    def test_render_text_alignment(self):
        data = self._binie(
            [
                self._text("Left", text_align=1),
                self._text("Right", y=-180, text_align=2),
                self._text("Center", y=-360, text_align=3),
            ]
        )
        _renderer, result = self._render(data)
        content = self._pages(result)[0]
        texts = self._texts(content)
        rects = self._rects(content)
        right_edge = 11.34 + PRINTABLE_WIDTH / 20.0

        self.assertAlmostEqual(texts[0][0], 11.34, places=2)
        self.assertAlmostEqual(texts[1][0] + rects[1][2], right_edge, places=2)
        self.assertAlmostEqual(
            texts[2][0] + rects[2][2] / 2.0,
            11.34 + (PRINTABLE_WIDTH // 2) / 20.0,
            delta=0.05,
        )

        self.assertAlmostEqual(texts[1][1], 841.89 - 9 - CALIBRI_ASCENT, places=2)
        self.assertAlmostEqual(texts[2][1], 841.89 - 18 - CALIBRI_ASCENT, places=2)

    def test_render_text_margins(self):
        data = self._binie(
            [
                self._text("Left", margin_left=50),
                self._text("Right", text_align=2, margin_right=40),
            ]
        )
        _renderer, result = self._render(data)
        content = self._pages(result)[0]
        texts = self._texts(content)
        rects = self._rects(content)
        self.assertAlmostEqual(texts[0][0], 11.34 + 50, places=2)
        self.assertAlmostEqual(
            texts[1][0] + rects[1][2], 11.34 + PRINTABLE_WIDTH / 20.0 - 40, places=2
        )

    def test_render_text_block(self):
        data = self._binie(
            [
                self._text(
                    "Left",
                    position_x=1000,
                    position_y=2000,
                    block_width=3000,
                    block_height=500,
                ),
                self._text(
                    "Right",
                    text_align=2,
                    position_x=1000,
                    position_y=2000,
                    block_width=3000,
                    block_height=500,
                ),
            ]
        )
        _renderer, result = self._render(data)
        content = self._pages(result)[0]
        texts = self._texts(content)
        rects = self._rects(content)
        self.assertAlmostEqual(texts[0][0], 11.34 + 50, places=2)
        self.assertAlmostEqual(texts[0][1], 841.89 - 100 - CALIBRI_ASCENT, places=2)
        self.assertAlmostEqual(texts[1][0] + rects[1][2], 11.34 + 200, places=2)

    def test_render_text_style(self):
        data = self._binie(
            [
                self._text("Bold", text_weight=1),
                self._text("Italic", y=-180, text_italic=1),
                self._text("Both", y=-360, text_weight=1, text_italic=1),
            ]
        )
        renderer, _result = self._render(data)
        self.assertEqual(renderer.fonts[("Calibri", "bold")][0], "calibrib")
        self.assertEqual(renderer.fonts[("Calibri", "italic")][0], "calibrii")
        self.assertEqual(renderer.fonts[("Calibri", "bold_italic")][0], "calibriz")

    def test_render_text_unknown_alignment(self):
        data = self._binie(
            [
                self._text(
                    "Unknown",
                    text_align=0,
                    margin_left=10,
                    position_x=1000,
                    position_y=2000,
                    block_width=3000,
                    block_height=500,
                )
            ]
        )
        _renderer, result = self._render(data)
        texts = self._texts(self._pages(result)[0])
        self.assertAlmostEqual(texts[0][0], 11.34 + 10, places=2)
        self.assertAlmostEqual(texts[0][1], 841.89 - 100 - CALIBRI_ASCENT, places=2)

    def test_render_image(self):
        data = self._binie(
            [
                self._image(text_align=1),
                self._image(y=-100, text_align=2),
                self._image(y=-200, text_align=3),
            ]
        )
        _renderer, result = self._render(data)
        images = self._images(self._pages(result)[0])
        right_edge = 11.34 + PRINTABLE_WIDTH / 20.0

        width, height, x, y = images[0]
        self.assertEqual((width, height), (10.0, 5.0))
        self.assertAlmostEqual(x, 11.34, places=2)
        self.assertAlmostEqual(y, 841.89 - 5, places=2)

        width, height, x, y = images[1]
        self.assertAlmostEqual(x + width, right_edge, places=2)
        self.assertAlmostEqual(y, 841.89 - 5 - 5, places=2)

        width, height, x, y = images[2]
        self.assertAlmostEqual(x, 11.34 + (PRINTABLE_WIDTH // 2 - 100) / 20.0, places=2)
        self.assertAlmostEqual(y, 841.89 - 10 - 5, places=2)

    def test_render_image_block(self):
        data = self._binie(
            [
                self._image(
                    position_x=2000,
                    position_y=20000,
                    block_width=1000,
                    block_height=1000,
                )
            ]
        )
        renderer, result = self._render(data)
        width, height, x, y = self._images(self._pages(result)[0])[0]
        self.assertAlmostEqual(x, 11.34 + 100, places=2)
        self.assertAlmostEqual(y, 841.89 - 1000 - 5, places=2)
        self.assertEqual(renderer.current_page, 0)
        self.assertEqual(len(self._pages(result)), 1)

    def test_render_image_unknown_alignment(self):
        data = self._binie(
            [
                self._image(
                    text_align=0,
                    position_x=2000,
                    position_y=2000,
                    block_width=1000,
                    block_height=1000,
                )
            ]
        )
        _renderer, result = self._render(data)
        width, height, x, y = self._images(self._pages(result)[0])[0]
        self.assertAlmostEqual(x, 11.34, places=2)
        self.assertAlmostEqual(y, 841.89 - 100 - 5, places=2)

    def test_ensure_page(self):
        data = self._binie(
            [self._text("First"), self._text("Second", y=-16900), self._image(y=-17100)]
        )
        renderer, result = self._render(data)
        pages = self._pages(result)
        self.assertEqual(len(pages), 2)
        self.assertEqual(renderer.current_page, 1)
        self.assertEqual(renderer.page_offset, 16837)

        texts = self._texts(pages[1])
        self.assertEqual(texts[0][4], b"Second")
        self.assertAlmostEqual(
            texts[0][1], 841.89 - 63 / 20.0 - CALIBRI_ASCENT, places=2
        )

        width, height, x, y = self._images(pages[1])[0]
        self.assertAlmostEqual(y, 841.89 - 263 / 20.0 - 5, places=2)

    def test_ensure_page_top(self):
        data = self._binie([self._text("First"), self._text("Second", y=-16830)])
        renderer, result = self._render(data)
        pages = self._pages(result)
        self.assertEqual(len(pages), 2)
        self.assertEqual(renderer.page_offset, 16830)
        texts = self._texts(pages[1])
        self.assertAlmostEqual(texts[0][1], 841.89 - CALIBRI_ASCENT, places=2)

    def test_ensure_font(self):
        renderer = colony_print.BinieRenderer()
        name, units_per_em, win_ascent, win_descent = renderer.ensure_font("Calibri")
        self.assertEqual(name, "calibri")
        self.assertEqual((units_per_em, win_ascent, win_descent), (2048, 1950, 550))
        self.assertEqual(renderer.ensure_font("Calibri", bold=True)[0], "calibrib")
        self.assertEqual(renderer.ensure_font("Calibri", italic=True)[0], "calibrii")
        self.assertEqual(
            renderer.ensure_font("Calibri", bold=True, italic=True)[0], "calibriz"
        )
        self.assertEqual(len(renderer.fonts), 4)

        renderer.fonts[("Calibri", "regular")] = ("cached", 1, 2, 3)
        self.assertEqual(renderer.ensure_font("Calibri"), ("cached", 1, 2, 3))

    def test_ensure_font_files(self):
        file_path = os.path.join(self.target_dir, "a" * 32 + ".ttf")
        with open(file_path, "wb") as file:
            file.write(build_font())

        renderer = colony_print.BinieRenderer(
            font_files={("colonia", "regular"): file_path}
        )
        renderer._match_font = lambda font_name, bold=False, italic=False: None
        name, units_per_em, win_ascent, win_descent = renderer.ensure_font("Colonia")
        self.assertEqual(name, "a" * 32)
        self.assertEqual((units_per_em, win_ascent, win_descent), (2048, 1950, 550))
        self.assertEqual(renderer.ensure_font("COLONIA", bold=True)[0], "a" * 32)
        self.assertEqual(renderer.ensure_font("Calibri")[0], "calibri")

        data = self._binie([self._text("Hello World", font=b"Colonia")])
        renderer = colony_print.BinieRenderer(
            size=RECEIPT_SIZE,
            margins=RECEIPT_MARGINS,
            font_files={("colonia", "regular"): file_path},
        )
        file = appier.legacy.BytesIO()
        renderer.render(data, file)
        self.assertEqual(b"Colonia" in file.getvalue(), True)

        # another file of the font (eg: a newer version, with the same face)
        # is the one used, even if the font was registered before
        updated_path = os.path.join(self.target_dir, "b" * 32 + ".ttf")
        with open(updated_path, "wb") as file:
            file.write(build_font() + b"\0")
        renderer = colony_print.BinieRenderer(
            font_files={("colonia", "regular"): updated_path}
        )
        renderer._match_font = lambda font_name, bold=False, italic=False: None
        self.assertEqual(renderer.ensure_font("Colonia")[0], "b" * 32)
        font = reportlab.pdfbase.pdfmetrics.getFont("b" * 32)
        self.assertEqual(font.face.filename, updated_path)

    def test_ensure_font_files_style(self):
        # the font of the system with the exact style (bold) is used before
        # the other style of the font installed on demand, as windows does
        file_path = os.path.join(self.target_dir, "c" * 32 + ".ttf")
        shutil.copyfile(os.path.join(FONTS_PATH, "calibri.ttf"), file_path)
        renderer = colony_print.BinieRenderer(
            font_files={("calibri", "regular"): file_path}
        )
        renderer._match_font = lambda font_name, bold=False, italic=False: None
        self.assertEqual(renderer.ensure_font("Calibri")[0], "c" * 32)
        self.assertEqual(renderer.ensure_font("Calibri", bold=True)[0], "calibrib")

        # without the font of the system the other style is used instead
        colony_print.printing.pdf.visitor.FONT_PATHS = (
            os.path.join(self.target_dir, ""),
        )
        renderer = colony_print.BinieRenderer(
            font_files={("calibri", "regular"): file_path}
        )
        renderer._match_font = lambda font_name, bold=False, italic=False: None
        self.assertEqual(renderer.ensure_font("Calibri", bold=True)[0], "c" * 32)

    def test_ensure_font_fallback(self):
        colony_print.printing.pdf.visitor.FONT_PATHS = (
            os.path.join(self.target_dir, ""),
        )
        with open(os.path.join(self.target_dir, "calibri.ttf"), "wb") as file:
            file.write(b"not a valid true type font")

        renderer = colony_print.BinieRenderer()
        calls = []

        def match_font(font_name, bold=False, italic=False):
            calls.append((font_name, bold, italic))
            return os.path.join(FONTS_PATH, "calibriz.ttf")

        renderer._match_font = match_font
        name, units_per_em, _win_ascent, _win_descent = renderer.ensure_font("Calibri")
        self.assertEqual(name, "calibriz")
        self.assertEqual(units_per_em, 2048)
        self.assertEqual(calls, [("Calibri", False, False)])

    def test_ensure_font_invalid(self):
        colony_print.printing.pdf.visitor.FONT_PATHS = (
            os.path.join(self.target_dir, ""),
        )
        renderer = colony_print.BinieRenderer()
        renderer._match_font = lambda font_name, bold=False, italic=False: None
        self.assertRaises(
            colony_print.InvalidFont, lambda: renderer.ensure_font("Unknown")
        )

    def test_position(self):
        renderer = colony_print.BinieRenderer()
        renderer.origin = (11.34, 841.89)
        self.assertEqual(renderer.position(0, 0), (11.34, 841.89))
        x, y = renderer.position(200, -400)
        self.assertAlmostEqual(x, 21.34, places=2)
        self.assertAlmostEqual(y, 821.89, places=2)

    @unittest.skipIf(os.name == "nt", "fontconfig is not available in windows")
    def test_match_font(self):
        arguments_path = os.path.join(self.target_dir, "arguments")
        script_path = os.path.join(self.target_dir, "fc-match")
        with open(script_path, "w") as file:
            file.write(
                '#!/bin/sh\nprintf "%%s" "$*" > "%s"\nprintf "/fonts/matched.ttf"\n'
                % arguments_path
            )
        os.chmod(script_path, 0o755)

        path = os.environ.get("PATH", "")
        os.environ["PATH"] = self.target_dir + os.pathsep + path
        try:
            renderer = colony_print.BinieRenderer()
            result = renderer._match_font("Font-Name:A", bold=True, italic=True)
        finally:
            os.environ["PATH"] = path

        self.assertEqual(result, "/fonts/matched.ttf")
        with open(arguments_path, "r") as file:
            arguments = file.read().strip()
        self.assertEqual(
            arguments,
            "--format=%{file} Font\\-Name\\:A:fontformat=TrueType:bold:italic",
        )

    def test_match_font_missing(self):
        path = os.environ.get("PATH", "")
        os.environ["PATH"] = self.target_dir
        try:
            renderer = colony_print.BinieRenderer()
            result = renderer._match_font("Calibri")
        finally:
            os.environ["PATH"] = path
        self.assertEqual(result, None)

    def test_string(self):
        renderer = colony_print.BinieRenderer()
        self.assertEqual(renderer._string(b"Calibri\0\0\0"), appier.legacy.u("Calibri"))
        self.assertEqual(
            renderer._string(appier.legacy.u("Ródio\0").encode("utf-8")),
            appier.legacy.u("Ródio"),
        )
        self.assertEqual(renderer._string(b"\0garbage"), appier.legacy.u(""))

    def test_valid_binie(self):
        data = self._binie([self._text("Hello World"), self._image()])
        self.assertEqual(colony_print.valid_binie(data), True)
        self.assertEqual(colony_print.valid_binie(self._binie([])), True)
        self.assertEqual(colony_print.valid_binie(data[:-1]), False)
        self.assertEqual(colony_print.valid_binie(data + b"\0"), False)
        self.assertEqual(colony_print.valid_binie(data[:100]), False)
        self.assertEqual(colony_print.valid_binie(b"%PDF-1.4\n" + b"\0" * 300), False)
        self.assertEqual(colony_print.valid_binie(self._binie([(3, b"\0" * 16)])), True)
        self.assertEqual(
            colony_print.valid_binie(self._binie([(3, b"\0" * 16)])[:-1]), False
        )

        count_data = struct.pack("<256sIII", b"test", 0, 0, 3) + data[268:]
        self.assertEqual(colony_print.valid_binie(count_data), False)
