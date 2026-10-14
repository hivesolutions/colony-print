#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import json
import shutil
import tempfile
import unittest
import subprocess

import appier

import PIL.Image

import colony_print

RESOURCES_PATH = os.path.join(os.path.dirname(__file__), "resources")
""" The path to the directory that contains the documents (and
the printer description) used by the end to end tests """

FONTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "..", "assets", "fonts"
)
""" The path to the directory that contains the fonts bundled
with the repository, used by every renderer of the tests """

FONT_FILES = {
    ("calibri", "regular"): "calibri.ttf",
    ("calibri", "bold"): "calibrib.ttf",
    ("calibri", "italic"): "calibrii.ttf",
    ("calibri", "bold_italic"): "calibriz.ttf",
}
""" The map associating the name and the style of the fonts used
by the documents with their (bundled) files """

PRINTABLE_WIDTH = 204.09
""" The width (in points) of the printable area of the receipts,
the 72 mm of a typical 80 mm roll receipt printer """

PAPER_HEIGHT = 841.89
""" The height (in points) of the paper, a 297 mm long roll """

SHEET_MARGIN = 113.39
""" The (left and right) margin of the sheet (in points) around
the printable area, wide enough for the texts that go beyond the
printable area to be visible (and measured) in the output """

SHEET_SIZE = (PRINTABLE_WIDTH + 2 * SHEET_MARGIN, PAPER_HEIGHT)
""" The size (in points) of the sheet of the Binie renderers, the
same of the paper of the end to end printer (`receipt.ppd`) """

RESOLUTION = 150
""" The resolution (in dpi) used to rasterize the outputs of the
renderers, for the analysis of their layout """

POSITION_TOLERANCE = 1.0
""" The tolerance (in points) for the vertical position of the
lines of text in the outputs of the different renderers, about
two pixels of the rasterized outputs """

EXTENT_TOLERANCE = 3.0
""" The minimum tolerance (in points) for the horizontal extent of
the lines of text in the outputs of the different renderers """

EXTENT_RATIO = 0.03
""" The tolerance for the horizontal extent of the lines of text,
relative to the width of the line, as the renderers measure the
texts with the same font files but GDI rounds (and hints) their
metrics, drawing them about 2% narrower """

SEGMENT_GAP = 8.0
""" The widest gap (in points) between the runs of ink of a line of
text that are part of the same segment, wider than the gaps between
the words of a text (up to about 3.5 points in the documents) and
narrower than the gaps between the texts placed by the margins of
a line (at least about 14 points in the documents) """

GDI_SCRIPT = """# -*- coding: utf-8 -*-
import sys
import json
import base64

import npcolony

with open(sys.argv[1], "r") as file:
    args = json.load(file)
for path in args["fonts"]:
    npcolony.load_font(path)
with open(args["binie"], "rb") as file:
    data = file.read()
data_b64 = base64.b64encode(data).decode("ascii")
result = npcolony.print_printer_base64(
    args["printer"], data_b64, dict(output_path=args["output"], title="e2e")
)
sys.exit(1 if result else 0)
"""
""" The script run by the Windows Python (under Wine) that prints
a Binie document through the GDI renderer of npcolony, loading the
fonts of the document as private fonts and writing the output of
the printer driver (PostScript) into a file """


def ink_lines(image, offset=0.0, resolution=RESOLUTION):
    """
    Retrieves the lines of text of the provided (grayscale) image, as the
    bands of rows with ink, each one split into its segments, the runs of
    ink separated by gaps wider than the spaces between the words.

    :type image: Image
    :param image: The grayscale image (rasterized page) to be analyzed.
    :type offset: float
    :param offset: The horizontal offset (in points) of the printable
    area in the page, so that the positions are relative to it.
    :type resolution: int
    :param resolution: The resolution (in dpi) of the image.
    :rtype: List
    :return: The lines of text, each one a map with the top and bottom
    positions, the left and right ink extents and the segments (pairs of
    left and right extents), in points relative to the top left corner
    of the printable area.
    """

    width, height = image.size
    pixels = image.load()
    scale = 72.0 / resolution

    # finds the columns with ink in every row of the image, grouping
    # the consecutive rows with ink (allowing small gaps, the accents)
    # into the bands that represent the lines of text
    bands, current, gap = [], None, 0
    for y in range(height):
        columns = [x for x in range(width) if pixels[x, y] < 128]
        if columns:
            if current and gap <= 2:
                current["bottom"] = y
                current["columns"].update(columns)
            else:
                current = dict(top=y, bottom=y, columns=set(columns))
                bands.append(current)
            gap = 0
        else:
            gap += 1

    # splits the columns with ink of every band into its segments, joining
    # the runs of ink separated by gaps that are not wider than the segment
    # gap, converting the positions into points relative to the printable
    # area (the end of each segment being the end of its last column)
    lines = []
    for band in bands:
        segments = []
        for x in sorted(band["columns"]):
            if segments and (x - segments[-1][1]) * scale <= SEGMENT_GAP:
                segments[-1][1] = x + 1
            else:
                segments.append([x, x + 1])
        segments = [
            (left * scale - offset, right * scale - offset) for left, right in segments
        ]
        lines.append(
            dict(
                top=band["top"] * scale,
                bottom=(band["bottom"] + 1) * scale,
                left=segments[0][0],
                right=segments[-1][1],
                segments=segments,
            )
        )
    return lines


class InkLinesTest(unittest.TestCase):
    def _image(self, boxes, size=(100, 40), color=0):
        image = PIL.Image.new("L", size, 255)
        for box in boxes:
            image.paste(color, box)
        return image

    def test_ink_lines(self):
        image = self._image(
            [(10, 5, 20, 15), (30, 5, 40, 15), (10, 25, 20, 30), (23, 25, 33, 30)]
        )
        lines = ink_lines(image, resolution=72)
        self.assertEqual(
            lines,
            [
                dict(
                    top=5.0,
                    bottom=15.0,
                    left=10.0,
                    right=40.0,
                    segments=[(10.0, 20.0), (30.0, 40.0)],
                ),
                dict(
                    top=25.0,
                    bottom=30.0,
                    left=10.0,
                    right=33.0,
                    segments=[(10.0, 33.0)],
                ),
            ],
        )

    def test_ink_lines_empty(self):
        self.assertEqual(ink_lines(self._image([]), resolution=72), [])

    def test_ink_lines_threshold(self):
        image = self._image([(10, 5, 20, 15)], color=128)
        self.assertEqual(ink_lines(image, resolution=72), [])

        image = self._image([(10, 5, 20, 15)], color=127)
        self.assertEqual(len(ink_lines(image, resolution=72)), 1)

    def test_ink_lines_rows(self):
        image = self._image([(10, 5, 20, 8), (10, 10, 20, 15)])
        lines = ink_lines(image, resolution=72)
        self.assertEqual(len(lines), 1)
        self.assertEqual((lines[0]["top"], lines[0]["bottom"]), (5.0, 15.0))

        image = self._image([(10, 5, 20, 8), (10, 11, 20, 15)])
        lines = ink_lines(image, resolution=72)
        self.assertEqual(len(lines), 2)
        self.assertEqual((lines[0]["top"], lines[0]["bottom"]), (5.0, 8.0))
        self.assertEqual((lines[1]["top"], lines[1]["bottom"]), (11.0, 15.0))

    def test_ink_lines_rows_extents(self):
        image = self._image([(30, 5, 40, 8), (10, 10, 20, 15)])
        lines = ink_lines(image, resolution=72)
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["segments"], [(10.0, 20.0), (30.0, 40.0)])

    def test_ink_lines_gap(self):
        image = self._image([(10, 5, 20, 15), (28, 5, 35, 15)])
        lines = ink_lines(image, resolution=72)
        self.assertEqual(lines[0]["segments"], [(10.0, 35.0)])

        image = self._image([(10, 5, 20, 15), (29, 5, 35, 15)])
        lines = ink_lines(image, resolution=72)
        self.assertEqual(lines[0]["segments"], [(10.0, 20.0), (29.0, 35.0)])

    def test_ink_lines_offset(self):
        image = self._image([(10, 5, 20, 15), (30, 5, 40, 15)])
        lines = ink_lines(image, offset=15.0, resolution=72)
        self.assertEqual(lines[0]["left"], -5.0)
        self.assertEqual(lines[0]["right"], 25.0)
        self.assertEqual(lines[0]["segments"], [(-5.0, 5.0), (15.0, 25.0)])
        self.assertEqual((lines[0]["top"], lines[0]["bottom"]), (5.0, 15.0))

    def test_ink_lines_resolution(self):
        image = self._image([(10, 5, 20, 15), (25, 5, 30, 15)])
        lines = ink_lines(image)
        scale = 72.0 / RESOLUTION
        self.assertEqual(lines[0]["top"], 5 * scale)
        self.assertEqual(lines[0]["bottom"], 15 * scale)
        self.assertEqual(lines[0]["segments"], [(10 * scale, 30 * scale)])


class EndToEndTest(unittest.TestCase):
    """
    End to end tests of the printing of XMPL documents, comparing the
    layout of the PDF documents generated by Colony Print (directly from
    XMPL and from Binie) with the one of the GDI renderer of npcolony, that
    prints the same Binie document under Wine.

    These tests require Wine (with a Windows Python that has npcolony,
    `E2E_PYTHON`), a printer that uses the `receipt.ppd` description
    (`E2E_PRINTER`), Ghostscript and Poppler, and only run when `E2E`
    is set, the outputs being kept in `E2E_OUTPUT` (when defined).
    """

    def setUp(self):
        if not appier.conf("E2E", False, cast=bool):
            self.skipTest("End to end tests are not enabled (E2E)")
        self.font_paths = colony_print.printing.pdf.visitor.FONT_PATHS
        colony_print.printing.pdf.visitor.FONT_PATHS = (os.path.join(FONTS_PATH, ""),)
        self.manager = colony_print.PrintingManager()
        self.manager.load()
        self.target_dir = tempfile.mkdtemp(prefix="colony-print-e2e-test-")
        self.output_dir = appier.conf("E2E_OUTPUT", None)

    def tearDown(self):
        colony_print.printing.pdf.visitor.FONT_PATHS = self.font_paths
        self.manager.unload()
        shutil.rmtree(self.target_dir, ignore_errors=True)

    def test_layout(self):
        outputs = self._print("layout")
        for name in ("binie_pdf", "binie_gdi"):
            self._assert_layout(outputs["xmpl_pdf"], outputs[name], name)
        for name in ("binie_pdf", "binie_gdi"):
            self.assertEqual(self._overflows(outputs[name]), [])

    def test_receipt(self):
        outputs = self._print("receipt")
        for name in ("binie_pdf", "binie_gdi"):
            self._assert_layout(outputs["xmpl_pdf"], outputs[name], name)

        # the two lines of the notes are the only ones that go beyond
        # the printable area, in both renderers of the Binie document
        overflows_pdf = self._overflows(outputs["binie_pdf"])
        overflows_gdi = self._overflows(outputs["binie_gdi"])
        self.assertEqual(len(overflows_pdf), 2)
        self.assertEqual(len(overflows_gdi), 2)
        for line_pdf, line_gdi in zip(overflows_pdf, overflows_gdi):
            message = "%s against %s" % (line_gdi, line_pdf)
            tolerance = max(
                EXTENT_TOLERANCE, EXTENT_RATIO * (line_pdf["right"] - line_pdf["left"])
            )
            self.assertAlmostEqual(
                line_pdf["top"], line_gdi["top"], delta=POSITION_TOLERANCE, msg=message
            )
            self.assertAlmostEqual(
                line_pdf["left"], line_gdi["left"], delta=tolerance, msg=message
            )
            self.assertAlmostEqual(
                line_pdf["right"], line_gdi["right"], delta=tolerance, msg=message
            )

    def test_receipt_wrap(self):
        outputs = self._print("receipt", wrap=True)
        for name in ("binie_pdf", "binie_gdi"):
            self._assert_layout(outputs["xmpl_pdf"], outputs[name], name)

        # the wrapping of the long texts is not yet supported by the
        # renderers (hivesolutions/colony-npapi#7), so the two lines of
        # the notes still go beyond the printable area, once the wrap
        # flag of Binie 1.1 is implemented no line must go beyond it
        self.assertEqual(len(self._overflows(outputs["binie_pdf"])), 2)
        self.assertEqual(len(self._overflows(outputs["binie_gdi"])), 2)

    def _print(self, name, wrap=False):
        """
        Prints the XMPL document with the provided name (from the resources)
        with every renderer, returning the lines of text of their outputs.

        :type name: String
        :param name: The name of the XMPL document in the resources.
        :type wrap: bool
        :param wrap: If the text wrapping should be requested for the
        texts of the document that disable it (the notes of the receipt).
        :rtype: Dictionary
        :return: The map associating the name of each renderer with the
        lines of text of its output.
        """

        with open(os.path.join(RESOURCES_PATH, name + ".xml"), "rb") as file:
            data = file.read().decode("utf-8")
        if wrap:
            data = data.replace('text_wrap="nowrap"', 'text_wrap="wrap"')
            name += "_wrap"

        xmpl_pdf = self._convert(data, "pdf", size=(PRINTABLE_WIDTH, PAPER_HEIGHT))
        binie = self._convert(data, "binie")
        self.assertEqual(colony_print.valid_binie(binie), True)
        binie_pdf = self._render(binie)
        binie_gdi = self._print_gdi(binie, name)

        self._store(name + ".binie", binie)
        outputs = dict()
        for renderer, data, offset in (
            ("xmpl_pdf", xmpl_pdf, 0.0),
            ("binie_pdf", binie_pdf, SHEET_MARGIN),
            ("binie_gdi", binie_gdi, SHEET_MARGIN),
        ):
            self._store("%s_%s.pdf" % (name, renderer), data)
            outputs[renderer] = self._lines(data, offset, "%s_%s" % (name, renderer))
        return outputs

    def _convert(self, data, format, size=None):
        file = appier.legacy.BytesIO()
        options = dict(name=format, file=file)
        if size:
            options["size"] = size
        self.manager.print_language(data, options)
        return file.getvalue()

    def _render(self, data):
        font_files = dict(
            (key, os.path.join(FONTS_PATH, value)) for key, value in FONT_FILES.items()
        )
        renderer = colony_print.BinieRenderer(
            size=SHEET_SIZE,
            margins=(SHEET_MARGIN, 0.0, SHEET_MARGIN, 0.0),
            font_files=font_files,
        )
        file = appier.legacy.BytesIO()
        renderer.render(data, file)
        return file.getvalue()

    def _print_gdi(self, data, name):
        """
        Prints the provided Binie document through the GDI renderer of
        npcolony, using the Windows Python (under Wine) and the end to
        end printer, returning the output converted into PDF.

        :type data: String
        :param data: The Binie document to be printed.
        :type name: String
        :param name: The name of the document, used for the files.
        :rtype: String
        :return: The PDF document with the output of the printer.
        """

        binie_path = os.path.join(self.target_dir, name + ".binie")
        script_path = os.path.join(self.target_dir, "gdi.py")
        args_path = os.path.join(self.target_dir, name + ".json")
        ps_path = os.path.join(self.target_dir, name + ".ps")
        pdf_path = os.path.join(self.target_dir, name + "_gdi.pdf")

        with open(binie_path, "wb") as file:
            file.write(data)
        with open(script_path, "w") as file:
            file.write(GDI_SCRIPT)
        with open(args_path, "w") as file:
            json.dump(
                dict(
                    fonts=[
                        self._windows_path(os.path.join(FONTS_PATH, value))
                        for value in sorted(FONT_FILES.values())
                    ],
                    binie=self._windows_path(binie_path),
                    printer=appier.conf("E2E_PRINTER", "colony-print-e2e"),
                    output=self._windows_path(ps_path),
                ),
                file,
            )

        env = dict(os.environ)
        env.setdefault("WINEDEBUG", "-all")
        env.setdefault("WINEDLLOVERRIDES", "mscoree,mshtml=")
        # runs the script with explicit standard streams, as the Windows
        # Python fails to start under (older versions of) Wine when they
        # are inherited from a process that has no console (eg: CI runners)
        log_path = os.path.join(self.target_dir, name + ".log")
        with open(os.devnull, "rb") as stdin, open(log_path, "wb") as log:
            result = subprocess.call(
                [
                    appier.conf("E2E_WINE", "wine"),
                    appier.conf("E2E_PYTHON"),
                    self._windows_path(script_path),
                    self._windows_path(args_path),
                ],
                stdin=stdin,
                stdout=log,
                stderr=log,
                env=env,
            )
        with open(log_path, "rb") as file:
            output = file.read().decode("utf-8", "replace")
        self.assertEqual(result, 0, output)
        subprocess.check_call(["ps2pdf", ps_path, pdf_path])
        with open(pdf_path, "rb") as file:
            return file.read()

    def _lines(self, data, offset, name):
        """
        Rasterizes the first page of the provided PDF document and
        retrieves its lines of text, as the bands of rows with ink.

        :type data: String
        :param data: The PDF document to be analyzed.
        :type offset: float
        :param offset: The horizontal offset (in points) of the printable
        area in the page, so that the positions are relative to it.
        :type name: String
        :param name: The name of the output, used for the files.
        :rtype: List
        :return: The lines of text, as retrieved by `ink_lines`.
        """

        pdf_path = os.path.join(self.target_dir, name + ".pdf")
        with open(pdf_path, "wb") as file:
            file.write(data)
        prefix = os.path.join(self.target_dir, name)
        subprocess.check_call(
            ["pdftoppm", "-r", str(RESOLUTION), "-gray", "-png", "-f", "1", "-l", "1"]
            + [pdf_path, prefix]
        )
        png_path = [
            os.path.join(self.target_dir, value)
            for value in os.listdir(self.target_dir)
            if value.startswith(name + "-") and value.endswith(".png")
        ][0]
        with open(png_path, "rb") as file:
            self._store(name + ".png", file.read())

        image = PIL.Image.open(png_path).convert("L")
        return ink_lines(image, offset=offset)

    def _overflows(self, lines):
        return [
            line
            for line in lines
            if line["left"] < -0.5 or line["right"] > PRINTABLE_WIDTH + 0.5
        ]

    def _assert_layout(self, reference, lines, name):
        """
        Asserts that the provided lines of text have the same layout of
        the reference ones, segment by segment, inside of the printable
        area (the reference being the direct conversion of XMPL into PDF,
        that has no room beyond the printable area).

        :type reference: List
        :param reference: The reference lines of text.
        :type lines: List
        :param lines: The lines of text to be verified.
        :type name: String
        :param name: The name of the renderer of the lines (for errors).
        """

        self.assertNotEqual(reference, [], name)
        self.assertEqual(len(lines), len(reference), name)
        for line_reference, line in zip(reference, lines):
            message = "%s: %s against %s" % (name, line, line_reference)
            self.assertAlmostEqual(
                line["top"],
                line_reference["top"],
                delta=POSITION_TOLERANCE,
                msg=message,
            )
            segments_reference = line_reference["segments"]
            self.assertEqual(len(line["segments"]), len(segments_reference), message)
            for segment_reference, segment in zip(segments_reference, line["segments"]):
                left = max(segment[0], 0.0)
                right = min(segment[1], PRINTABLE_WIDTH)
                tolerance = max(
                    EXTENT_TOLERANCE,
                    EXTENT_RATIO * (segment_reference[1] - segment_reference[0]),
                )
                self.assertAlmostEqual(
                    left, segment_reference[0], delta=tolerance, msg=message
                )
                self.assertAlmostEqual(
                    right, segment_reference[1], delta=tolerance, msg=message
                )

    def _store(self, name, data):
        if not self.output_dir:
            return
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        with open(os.path.join(self.output_dir, name), "wb") as file:
            file.write(data)

    def _windows_path(self, path):
        return "Z:" + os.path.abspath(path).replace("/", "\\")
