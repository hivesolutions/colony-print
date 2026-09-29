#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import math
import struct
import subprocess

import appier

import PIL.Image

from . import visitor
from . import exceptions

FONT_SCALE_FACTOR = 20
""" The scale factor that converts PDF points (eg: the
font size) into twips, the logical unit of binie documents """

IMAGE_SCALE_FACTOR = 10
""" The scale factor that converts the size of an image
(in pixels) into twips, so that images are printed at 144 dpi """

TWIPS_PER_INCH = 1440.0
""" The coefficient for conversion between twips and inches """

MM_PER_INCH = 25.4
""" The coefficient for conversion between millimeter and inch """

TEXT_VALUE = 1
""" The type value of the text elements of a binie document """

IMAGE_VALUE = 2
""" The type value of the image elements of a binie document """

LEFT_TEXT_ALIGN_VALUE = 1
""" The value of the left alignment of the elements """

RIGHT_TEXT_ALIGN_VALUE = 2
""" The value of the right alignment of the elements """

CENTER_TEXT_ALIGN_VALUE = 3
""" The value of the center alignment of the elements """

DOCUMENT_HEADER_FORMAT = "<256sIII"
""" The format of the header of a binie document, containing
the title, width, height and number of elements """

ELEMENT_HEADER_FORMAT = "<II"
""" The format of the header of each element of a binie
document, containing the type and the length of the element """

TEXT_HEADER_FORMAT = "<ii256sIIIIIIIIIII"
""" The format of the header of the text elements, that
is followed by the (null terminated) text itself """

IMAGE_HEADER_FORMAT = "<iiIIIIII"
""" The format of the header of the image elements, that
is followed by the (bitmap) image data """


class BinieRenderer(object):
    """
    The renderer that replays a binie document into a PDF file
    following the drawing rules of the windows (GDI) printing
    infra-structure, so that the same binie document results in
    the same layout in the printers of both systems.
    """

    size = None
    """ The default size (width and height) of the page in PDF
    points, used when the binie document defines no size """

    margins = None
    """ The margins of the page (left, bottom, right and top) in
    PDF points, the area outside of them is not printable """

    custom = True
    """ If the size defined by the binie document is used as the
    (custom) size of its pages, otherwise the pages always use the
    default size, as when the printer doesn't accept the size """

    fonts = {}
    """ The map associating the name and style of a font with the
    name and the metrics of the font loaded in the PDF context """

    canvas = None
    """ The reference to the canvas object to be used
    for manipulating the various PDF elements """

    origin = None
    """ The position of the top left corner of the printable area
    in PDF points, the origin of the binie coordinates """

    clip_box = None
    """ The default clip box (left, top, right and bottom) of the
    printable area measured in twips, as windows does """

    vertical_size = 0
    """ The height of the printable area in millimeters, used
    to control the creation of new pages """

    current_page = 0
    """ The index of the page that is currently being drawn """

    page_offset = 0
    """ The vertical offset (in twips) to be added to the elements
    as a result of the pages that have already been drawn """

    def __init__(self, size=None, margins=None, custom=True):
        """
        Constructor of the class.

        :type size: Tuple
        :param size: The default size (width and height in points) of
        the pages, used when the document doesn't define one.
        :type margins: Tuple
        :param margins: The margins (left, bottom, right and top in
        points) of the page, that delimit its printable area.
        :type custom: bool
        :param custom: If the size defined by the document is used as
        the (custom) size of its pages, as the custom paper size of
        windows, otherwise the pages always use the default size, as
        when the printer doesn't accept the size of the document.
        """

        self.size = size or visitor.PAPER_SIZE
        self.margins = margins or (0.0, 0.0, 0.0, 0.0)
        self.custom = custom
        self.fonts = {}
        self.canvas = None
        self.origin = None
        self.clip_box = None
        self.vertical_size = 0
        self.current_page = 0
        self.page_offset = 0

    def render(self, data, file):
        """
        Renders the provided binie document into the provided file as
        a PDF document, using the size defined in the document when it's
        available and used as a custom size (as windows does) and the
        default size otherwise, an exception is raised in case the data
        is not a valid binie document.

        :type data: String
        :param data: The binie document to be rendered as PDF.
        :type file: File
        :param file: The file object where the PDF document is
        going to be written.
        """

        import reportlab.pdfgen.canvas

        # verifies that the data is a (structurally) valid binie document
        # before reading any of its structure, raising an exception otherwise
        if not valid_binie(data):
            raise exceptions.InvalidBinie(
                "elements not matching the %d bytes of data" % len(data)
            )

        # unpacks the header of the document that contains the title,
        # the (optional) dimensions and the number of elements
        title, width, height, count = struct.unpack_from(DOCUMENT_HEADER_FORMAT, data)

        # uses the dimensions of the document as the size of the page
        # in case both are defined (tenths of millimeter) and used as a
        # custom size, just like the custom paper size of windows, otherwise
        # uses the default size (eg: the paper the printer is loaded with)
        if self.custom and width > 0 and height > 0:
            size = (width / 100.0 * visitor.SCALE, height / 100.0 * visitor.SCALE)
        else:
            size = self.size

        # calculates the printable area of the page (the page without
        # the margins), its top left corner is the origin of the binie
        # coordinates and its height controls the creation of new pages,
        # in whole millimeters (as windows does) rounded to hundredths
        # first, so that the rounding of the sizes of the printers (eg:
        # 283.46 points for 100 mm) doesn't take a millimeter away
        page_width, page_height = size
        margin_left, margin_bottom, margin_right, margin_top = self.margins
        printable_width = page_width - margin_left - margin_right
        printable_height = page_height - margin_bottom - margin_top
        self.origin = (margin_left, page_height - margin_top)
        self.clip_box = (
            0,
            0,
            int(printable_width * FONT_SCALE_FACTOR),
            int(printable_height * FONT_SCALE_FACTOR) * -1,
        )
        self.vertical_size = max(
            int(round(printable_height / visitor.INCH * MM_PER_INCH, 2)), 1
        )
        self.current_page = 0
        self.page_offset = 0

        # creates the canvas for the PDF document with the calculated
        # size and sets the title of the binie document in it
        self.canvas = reportlab.pdfgen.canvas.Canvas(file, pagesize=size)
        self.canvas.setTitle(self._string(title))

        # iterates over the complete set of elements of the document to
        # render each of them, note that unknown elements are ignored
        offset = struct.calcsize(DOCUMENT_HEADER_FORMAT)
        for _index in appier.legacy.xrange(count):
            element_type, element_length = struct.unpack_from(
                ELEMENT_HEADER_FORMAT, data, offset
            )
            offset += struct.calcsize(ELEMENT_HEADER_FORMAT)
            element = data[offset : offset + element_length]
            offset += element_length
            if element_type == TEXT_VALUE:
                self.render_text(element)
            elif element_type == IMAGE_VALUE:
                self.render_image(element)

        # saves the final canvas structure flushing the data to
        # the associated file object (final operation)
        self.canvas.save()

    def render_text(self, element):
        """
        Renders the provided text element of a binie document, the size
        of the font is the height of the font cell and the text is drawn
        from the top of its cell, as the windows (GDI) text output does.

        :type element: String
        :param element: The text element (without the element header)
        to be rendered in the current page.
        """

        # unpacks the header of the text element and then retrieves
        # the text (null terminated) that follows the header
        (
            _position_x,
            element_y,
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
            length,
        ) = struct.unpack_from(TEXT_HEADER_FORMAT, element)
        header_size = struct.calcsize(TEXT_HEADER_FORMAT)
        text = self._string(element[header_size : header_size + length])

        # loads the font of the text and calculates the size of the font
        # (em) for which the cell height is the font size, together with
        # the ascent of the cell (distance from its top to the baseline)
        font_name, units_per_em, win_ascent, win_descent = self.ensure_font(
            self._string(font), bold=text_weight > 0, italic=text_italic > 0
        )
        cell_size = win_ascent + win_descent or units_per_em
        em_size = float(font_size) * units_per_em / cell_size
        ascent = float(font_size) * win_ascent / cell_size

        # measures the size of the text (in twips), the width is the width
        # of the text and the height is the height of the font cell
        text_width = int(
            self.canvas.stringWidth(text, font_name, em_size) * FONT_SCALE_FACTOR
        )
        text_height = font_size * FONT_SCALE_FACTOR

        # retrieves the clip box of the text, the printable area or the
        # block (measured in twips) in case the text is inside a block
        clip_left, clip_top, clip_right, clip_bottom = self.clip_box
        is_block = not block_width == 0 and not block_height == 0
        if is_block:
            clip_left = position_x
            clip_top = position_y * -1
            clip_right = position_x + block_width
            clip_bottom = (position_y + block_height) * -1

        # calculates the horizontal position of the text taking into
        # account the margins of the text and the requested alignment
        text_x = (margin_left - margin_right) * FONT_SCALE_FACTOR
        if text_align == LEFT_TEXT_ALIGN_VALUE:
            text_x += clip_left
        elif text_align == RIGHT_TEXT_ALIGN_VALUE:
            text_x += clip_right - text_width
        elif text_align == CENTER_TEXT_ALIGN_VALUE:
            text_x += clip_left + (clip_right - clip_left) // 2 - text_width // 2

        # calculates the vertical position of the text and the position
        # of its bottom (in millimeters, rounded up) so that the proper
        # page is used for the text (creating a new one if required)
        text_y = clip_top + element_y
        text_y_bottom = clip_bottom if is_block else text_y - text_height
        bottom = (
            math.ceil(text_y_bottom / TWIPS_PER_INCH * MM_PER_INCH * -100.0) / 100.0
        )
        text_y = self.ensure_page(text_y, bottom=bottom)

        # draws the (white) background of the text cell, as windows does
        # in its opaque background mode, and then the text in its baseline
        x, y = self.position(text_x, text_y)
        self.canvas.setFillColorRGB(1.0, 1.0, 1.0)
        self.canvas.rect(
            x,
            y - font_size,
            text_width / float(FONT_SCALE_FACTOR),
            font_size,
            stroke=0,
            fill=1,
        )
        self.canvas.setFillColorRGB(0, 0, 0)
        self.canvas.setFont(font_name, em_size)
        self.canvas.drawString(x, y - ascent, text)

    def render_image(self, element):
        """
        Renders the provided image element of a binie document, the image
        is printed at 144 dpi from its top left corner and images inside
        blocks never create new pages, as windows (GDI) does.

        :type element: String
        :param element: The image element (without the element header)
        to be rendered in the current page.
        """

        import reportlab.lib.utils

        # unpacks the header of the image element and then loads the
        # (bitmap) image from the data that follows the header
        (
            _position_x,
            element_y,
            text_align,
            position_x,
            position_y,
            block_width,
            block_height,
            length,
        ) = struct.unpack_from(IMAGE_HEADER_FORMAT, element)
        header_size = struct.calcsize(IMAGE_HEADER_FORMAT)
        buffer = appier.legacy.BytesIO(element[header_size : header_size + length])
        bitmap_image = PIL.Image.open(buffer)

        # calculates the size of the image in twips, using the image
        # scale factor, meaning that images are printed at 144 dpi
        bitmap_width, bitmap_height = bitmap_image.size
        scaled_width = bitmap_width * IMAGE_SCALE_FACTOR
        scaled_height = bitmap_height * IMAGE_SCALE_FACTOR

        # retrieves the clip box of the image, the printable area or the
        # block (measured in twips) in case the image is inside a block
        clip_left, clip_top, clip_right, _clip_bottom = self.clip_box
        is_block = not block_width == 0 and not block_height == 0
        if is_block:
            clip_left = position_x
            clip_top = position_y * -1
            clip_right = position_x + block_width

        # calculates the horizontal position of the image according to
        # the requested alignment inside the clip box
        image_x = 0
        if text_align == LEFT_TEXT_ALIGN_VALUE:
            image_x = clip_left
        elif text_align == RIGHT_TEXT_ALIGN_VALUE:
            image_x = clip_right - scaled_width
        elif text_align == CENTER_TEXT_ALIGN_VALUE:
            image_x = clip_left + (clip_right - clip_left) // 2 - scaled_width // 2

        # calculates the position of the bottom of the image (in millimeters)
        # so that the proper page is used, images inside blocks are never
        # moved into a new page (clipping rules apply to them)
        image_y_bottom = clip_top - element_y + scaled_height
        bottom = None if is_block else image_y_bottom / TWIPS_PER_INCH * MM_PER_INCH
        image_y = self.ensure_page(clip_top + element_y, bottom=bottom)

        # draws the image from its top left corner with the size in points
        # (twips divided by the scale factor) at the calculated position
        x, y = self.position(image_x, image_y)
        width = scaled_width / float(FONT_SCALE_FACTOR)
        height = scaled_height / float(FONT_SCALE_FACTOR)
        image_reader = reportlab.lib.utils.ImageReader(bitmap_image)
        self.canvas.drawImage(image_reader, x, y - height, width, height)

    def ensure_page(self, y, bottom=None):
        """
        Ensures that the element with the provided bottom position is
        drawn in the proper page, creating a new page in case the bottom
        goes beyond the current page, as the windows implementation does.

        The returned vertical position takes into account the offset of
        the pages that have already been drawn.

        :type y: int
        :param y: The vertical position (in twips) of the top of the
        element, relative to the first page.
        :type bottom: float
        :param bottom: The position of the bottom of the element in
        millimeters, in case it's not provided no page is created.
        :rtype: int
        :return: The vertical position (in twips) of the top of the
        element in the current page.
        """

        # uses the bottom position of the element and divides it by the
        # page size to check the index of its page, creating a new page
        # in case it's after the current page
        new_page = (
            self.current_page if bottom == None else int(bottom / self.vertical_size)
        )
        if new_page > self.current_page:
            self.canvas.showPage()
            page_size_twips = self.vertical_size / MM_PER_INCH * TWIPS_PER_INCH
            self.current_page = new_page
            self.page_offset += int(page_size_twips)

        # adds the offset of the pages to the vertical position and resets
        # it in case it goes above the top of the page (positive value)
        y += self.page_offset
        if y > 0:
            self.page_offset -= y
            y = 0

        return y

    def ensure_font(self, font_name, bold=False, italic=False):
        """
        Ensures that the font with the provided name and style is loaded
        in the PDF context, returning its name in the context and the
        metrics used by windows to size the font.

        The font file is searched with the file name convention of the
        PDF visitor and, in case it's not found, the closest font installed
        in the system is used instead, as windows substitutes missing fonts.

        :type font_name: String
        :param font_name: The name of the font to be loaded (eg: Calibri).
        :type bold: bool
        :param bold: If the bold variant of the font should be loaded.
        :type italic: bool
        :param italic: If the italic variant of the font should be loaded.
        :rtype: Tuple
        :return: The name of the font in the PDF context, the number of
        units per em of the font and its (windows) ascent and descent.
        """

        import reportlab.pdfbase.ttfonts
        import reportlab.pdfbase.pdfmetrics

        # builds the style of the font and uses it to check if the font
        # is already loaded, returning its values immediately if that's
        # the case (avoids multiple loading of the font)
        if bold and italic:
            style = "bold_italic"
        elif bold:
            style = "bold"
        elif italic:
            style = "italic"
        else:
            style = "regular"
        key = (font_name, style)
        if key in self.fonts:
            return self.fonts[key]

        # creates the sequence of paths of the font files to be tried, first
        # the ones following the file name convention of the PDF visitor and
        # then the closest font installed in the system (substitution)
        file_name = font_name.lower() + visitor.FONT_SUFFIX_MAP[style] + ".ttf"
        file_paths = [
            os.path.expanduser(font_path + file_name)
            for font_path in visitor.FONT_PATHS
        ]
        file_paths.append(self._match_font(font_name, bold=bold, italic=italic))

        # iterates over the paths of the font files trying to load the font
        # and its metrics, the first valid one is the one to be used
        for file_path in file_paths:
            if not file_path:
                continue
            try:
                name = os.path.splitext(os.path.basename(file_path))[0]
                font = reportlab.pdfbase.ttfonts.TTFont(name, file_path)
                reportlab.pdfbase.pdfmetrics.registerFont(font)
                head = font.face.get_table("head")
                os2 = font.face.get_table("OS/2")
            except Exception:
                continue
            units_per_em = struct.unpack(">H", head[18:20])[0]
            win_ascent, win_descent = struct.unpack(">HH", os2[74:78])
            self.fonts[key] = (name, units_per_em, win_ascent, win_descent)
            return self.fonts[key]

        # raises an exception as it was not possible to load the font
        # neither from the expected file nor from the installed fonts
        raise exceptions.InvalidFont(
            "not possible to load '%s' - '%s'" % (font_name, file_name)
        )

    def position(self, x, y):
        """
        Converts the provided position in twips, relative to the top left
        corner of the printable area, into a position in PDF points.

        :type x: int
        :param x: The horizontal position in twips.
        :type y: int
        :param y: The vertical position in twips (negative downwards).
        :rtype: Tuple
        :return: The position in PDF points (origin in the bottom left
        corner of the page).
        """

        origin_x, origin_y = self.origin
        return (
            origin_x + x / float(FONT_SCALE_FACTOR),
            origin_y + y / float(FONT_SCALE_FACTOR),
        )

    def _match_font(self, font_name, bold=False, italic=False):
        """
        Retrieves the path to the file of the installed font that best
        matches the provided font name and style, using fontconfig.

        :type font_name: String
        :param font_name: The name of the font to be matched.
        :type bold: bool
        :param bold: If the bold variant of the font should be matched.
        :type italic: bool
        :param italic: If the italic variant of the font should be matched.
        :rtype: String
        :return: The path to the file of the matched font or an invalid
        value in case fontconfig is not available in the system.
        """

        # builds the fontconfig pattern for the font, escaping the name
        # and requiring a true type font (supported by the PDF context)
        pattern = font_name
        for character in ("\\", "-", ":", ","):
            pattern = pattern.replace(character, "\\" + character)
        pattern += ":fontformat=TrueType"
        if bold:
            pattern += ":bold"
        if italic:
            pattern += ":italic"

        # runs the fontconfig matching for the pattern, returning an
        # invalid value in case it's not available in the system
        try:
            file_path = subprocess.check_output(
                ["fc-match", "--format=%{file}", pattern]
            )
        except Exception:
            return None
        return file_path.decode("utf-8").strip() or None

    def _string(self, value):
        """
        Converts the provided (null terminated) binie string into an
        unicode string, ignoring the bytes after the first null one and
        the ones that are not valid UTF-8.

        :type value: String
        :param value: The binie string (bytes) to be converted.
        :rtype: String
        :return: The unicode string that the binie string represents.
        """

        return value.split(b"\0", 1)[0].decode("utf-8", "ignore")


def valid_binie(data):
    """
    Verifies if the provided data is a (structurally) valid binie
    document, meaning that the sequence of elements described in
    its header exactly matches the size of the data.

    :type data: String
    :param data: The data to be verified as a binie document.
    :rtype: bool
    :return: If the provided data is a valid binie document.
    """

    # verifies that the data is large enough to contain the header
    # of the document and then retrieves the number of elements
    header_size = struct.calcsize(DOCUMENT_HEADER_FORMAT)
    element_size = struct.calcsize(ELEMENT_HEADER_FORMAT)
    if len(data) < header_size:
        return False
    count = struct.unpack_from(DOCUMENT_HEADER_FORMAT, data)[3]

    # iterates over the elements of the document making sure that each
    # of them is contained in the data, the ones of unknown types included
    # as they are ignored while rendering (as the specification defines)
    offset = header_size
    for _index in appier.legacy.xrange(count):
        if offset + element_size > len(data):
            return False
        _element_type, element_length = struct.unpack_from(
            ELEMENT_HEADER_FORMAT, data, offset
        )
        offset += element_size + element_length

    # the document is only valid in case the elements end exactly
    # at the end of the data (no missing or extra data)
    return offset == len(data)
