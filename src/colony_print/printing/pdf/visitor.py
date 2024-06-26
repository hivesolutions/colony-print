#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import appier
import base64

import PIL.Image

from . import exceptions

from ..common.base import *
from ..manager.ast import *

try:
    import reportlab.lib.units
except ImportError:
    INCH = 72.0
    CM = INCH / 2.54
else:
    INCH = reportlab.lib.units.inch
    CM = reportlab.lib.units.cm

FONT_SCALE_FACTOR = 1
""" The font scale factor """

IMAGE_SCALE_FACTOR = 0.5
""" The image scale factor """

EXCLUSION_LIST = [
    "__class__",
    "__delattr__",
    "__dict__",
    "__doc__",
    "__getattribute__",
    "__hash__",
    "__init__",
    "__module__",
    "__new__",
    "__reduce__",
    "__reduce_ex__",
    "__repr__",
    "__setattr__",
    "__str__",
    "__weakref__",
    "__format__",
    "__sizeof__",
    "__subclasshook__",
    "accept",
    "accept_double",
    "accept_post_order",
    "add_child_node",
    "remove_child_node",
    "set_indent",
    "set_value",
    "indent",
    "value",
    "child_nodes",
]
""" The exclusion list """

FONT_SUFFIX_MAP = {"regular": "", "bold": "b", "italic": "i", "bold_italic": "z"}
""" The map associating the type of font
and the suffix to be appended to the name
to created the full font name """

DEFAULT_ENCODER = "utf-8"
""" The default encoder """

SCALE = CM
""" The scale value to be used in the conversion
of the centimeter value into the PDF point """

TWIP_SCALE = 0.001763889
""" The scale factor to convert a twip value into
a centimeter base value """

A4_PAPER = (21.0 * SCALE, 29.7 * SCALE)
""" The default size (dimensions) for an a4 paper
based structure, this includes the additional
margin values normally created by full size printers """

ROLL_PAPER = (7.2 * SCALE, 29.7 * SCALE)
""" The default size (dimensions) for a roll paper
based structure, this includes the additional
margin values normally created by receipt printers """

PAPER_SIZE = A4_PAPER
""" The default paper size to be used when no paper
size value is defined for the print operation """

FONT_PATHS = ("", "~/.fonts/", "/usr/share/fonts/truetype/")
""" The set of base paths to be used for searching
for fonts on the current system """


class Visitor(object):
    """
    The visitor class for the PDF printing infra-structure
    this visitor should be able to generate a PDF file
    using the reportlab library as basics.
    """

    node_method_map = {}
    """ The node method map """

    visit_childs = True
    """ The visit childs flag """

    visit_next = True
    """ The visit next flag """

    visit_index = 0
    """ The visit index, for multiple visits """

    options = {}
    """ The printing options """

    canvas = None
    """ The reference to the canvas object to be used
    for manipulating the various PDF elements """

    size = None
    """ The size of the document to be printed, this
    is the width and height measured in PDF points """

    width = None
    """ The width of the document to be printed, this
    is the width measured in PDF points """

    height = None
    """ The height of the document to be printed, this
    is the height measured in PDF points """

    single = False
    """ If the document to be parsed is considered to be
    single page only or multi page, this is relevant for
    the fixed/absolute positioning using blocks  """

    current_position = None
    """ The current position in the document measured
    as PDF points """

    fonts = {}
    """ The map containing the various loaded fonts
    to avoid multiple loading of fonts (redundancy is
    removed to avoid errors) """

    context_map = {}
    """ The context information map """

    def __init__(self):
        self.node_method_map = {}
        self.visit_childs = True
        self.visit_next = True
        self.visit_index = 0
        self.options = {}
        self.canvas = None
        self.width = 0
        self.height = 0
        self.single = False
        self.current_position = None
        self.fonts = {}
        self.context_map = {}

        self.update_node_method_map()

    def update_node_method_map(self):
        # retrieves the class of the current instance
        self_class = self.__class__

        # retrieves the names of the elements for the current class
        self_class_elements = dir(self_class)

        # iterates over all the name of the elements
        for self_class_element in self_class_elements:
            # retrieves the real element value
            self_class_real_element = getattr(self_class, self_class_element)

            # in case the current class real element does not contain
            # an AST node class reference must continue the loop
            if not hasattr(self_class_real_element, "ast_node_class"):
                continue

            # retrieves the AST node class from the current class real element
            # and sets it in the node method map
            ast_node_class = getattr(self_class_real_element, "ast_node_class")
            self.node_method_map[ast_node_class] = self_class_real_element

    def get_options(self):
        """
        Retrieves the printing options.

        :rtype: Dictionary
        :return: The printing options.
        """

        return self.options

    def set_options(self, options):
        """
        Sets the printing options.

        :type options: Dictionary.
        :param options: The printing options.
        """

        self.options = options

    @dispatch_visit()
    def visit(self, node):
        print("unrecognized element node of type " + node.__class__.__name__)

    def before_visit(self, node):
        self.visit_childs = True
        self.visit_next = True

    def after_visit(self, node):
        pass

    @visited(AstNode)
    def visit_ast_node(self, node):
        pass

    @visited(GenericElement)
    def visit_generic_element(self, node):
        pass

    @visited(PrintingDocument)
    def visit_printing_document(self, node):
        import reportlab.pdfgen.canvas

        # in case it's the first visit
        if self.visit_index == 0:
            # adds the node as the context information
            self.add_context(node)

            # retrieves both the file (buffer) to be used for the output
            # of the PDF file contents and the expected size for the PDF
            # document, in case no size is provided a default one is used
            file = self.options["file"]
            size = self.options.get("size", PAPER_SIZE)

            # tries to retrieve the document width and height values and
            # converts them into the proper integer values, these values
            # are mostly available for single page operations
            printing_document_width = hasattr(node, "width") and int(node.width) or 0
            printing_document_height = hasattr(node, "height") and int(node.height) or 0

            # in case both the printing document with and height values are
            # available the size tuple for the current document is defined
            # using their values, note that these values are defined as tenth
            # of the millimeter values (100 units equals 1 centimeter)
            if not printing_document_width == 0 and not printing_document_height == 0:
                size = (
                    printing_document_width / 100 * SCALE,
                    printing_document_height / 100 * SCALE,
                )

            # unpacks the size tuple into the width and height
            # components and sets the tuple containing both values
            # as the size to be used for the document
            self.width, self.height = size
            self.size = (self.width, self.height)

            # creates the canvas object to be used as the primary
            # entry point for operation on the PDF
            self.canvas = reportlab.pdfgen.canvas.Canvas(file, pagesize=self.size)

            # sets the initial position so that the "virtual" cursor
            # position is situated at the top left corner of the page
            self.current_position = (0, self.height)

        # in case it's the second visit
        elif self.visit_index == 1:
            # saves the final canvas structure flushing the data to
            # the associated file object, this is considered the final
            # operation for the creation of the PDF file
            self.canvas.save()

            # removes the context information
            self.remove_context(node)

    @visited(Block)
    def visit_block(self, node):
        if self.visit_index == 0:
            # adds the node as the context information, this way
            # the complete set of symbols for the block are exposed
            # to the underlying nodes (block opening)
            self.add_context(node)
            self.push_context("biggest_height", 0)

        # in case it's the second visit
        elif self.visit_index == 1:
            # removes the context information
            self.remove_context(node)

    @visited(Paragraph)
    def visit_paragraph(self, node):
        if self.visit_index == 0:
            self.add_context(node)
        elif self.visit_index == 1:
            self.remove_context(node)

    @visited(Line)
    def visit_line(self, node):
        if self.visit_index == 0:
            self.add_context(node)
            self.push_context("biggest_height", 0)

            # retrieves the margin top value defined
            # for the current context
            margin_top = int(self.get_context("margin_top", "0"))

            # retrieves the current position in x and y
            # and then updates the current position
            current_position_x, current_position_y = self.current_position
            self.current_position = (
                current_position_x,
                current_position_y - margin_top * FONT_SCALE_FACTOR,
            )

        elif self.visit_index == 1:
            biggest_height = self.get_context("biggest_height")
            self.pop_context("biggest_height")

            # retrieves the margin bottom value defined
            # for the current context
            margin_bottom = int(self.get_context("margin_bottom", "0"))

            # retrieves the current position in x and y
            # and then updates the current position
            current_position_x, current_position_y = self.current_position
            self.current_position = (
                0,
                current_position_y - biggest_height - margin_bottom * FONT_SCALE_FACTOR,
            )

            # removes the context information
            self.remove_context(node)

    @visited(Text)
    def visit_text(self, node):
        if self.visit_index == 0:
            # adds the node as the context information
            self.add_context(node)

            # retrieves the text and encodes it using
            # the default encoder and ignoring possible errors
            text_encoded = node.text.encode(DEFAULT_ENCODER, "ignore")

            # retrieves the complete set of attributes for the current
            # context to be used for the processing of the node
            font_name = str(self.get_context("font"))
            font_size = int(self.get_context("font_size"))
            text_align = self.get_context("text_align")
            font_style = self.get_context("font_style", "regular")
            margin_left = int(self.get_context("margin_left", "0"))
            margin_right = int(self.get_context("margin_right", "0"))
            position_x = int(self.get_context("x", "0"))
            position_y = int(self.get_context("y", "0"))
            block_width = int(self.get_context("width", "0"))
            block_height = int(self.get_context("height", "0"))

            # converts the various block related values from their original
            # twip based value into the PDF point value to be used in print
            position_x = int(position_x * TWIP_SCALE * SCALE)
            position_y = int(position_y * TWIP_SCALE * SCALE)
            block_width = int(block_width * TWIP_SCALE * SCALE)
            block_height = int(block_height * TWIP_SCALE * SCALE)

            # verifies if the current context is of type block, so that
            # the proper absolute positions are going to be used instead
            is_block = not block_width == 0 and not block_height == 0

            # sets the initial clip (box) value that will be applied in
            # case the current execution mode is not block based
            clip_left = 0
            clip_top = 0
            clip_right = self.width
            _clip_bottom = self.height

            # verifies if the current mode is block and if that's the case
            # re-calculates the new clip (box) value taking that into account
            if is_block:
                self.single = True
                clip_left = position_x
                clip_top = position_y * -1
                clip_right = position_x + block_width
                _clip_bottom = (position_y + block_height) * -1

            # calculates the resized font size so that it's normalized
            # according to the printing language specification, the value
            # is rounded to one decimal place so that no major visual
            # rounding problems occur
            font_size_r = round(font_size / 1.2, 1)

            # retrieves the proper suffix for the requested font style
            # and uses it to create the complete font name ensuring that
            # it's currently loaded in the PDF context
            suffix = FONT_SUFFIX_MAP.get(font_style, "")
            font_name_c = font_name + suffix
            self.ensure_font(font_name_c)

            # sets the complete computed font in the current canvas context
            # note that the leading value is overridden to avoid font sizing
            # problems in accordance with the printing language specification,
            # this is the "first" font setting and ensures that the measuring
            # of the font size is the correct one (required by algorithm)
            self.canvas.setFont(font_name_c, font_size_r, leading=1.0)

            # retrieves the current position in x and y unpacking the values
            # from the current position tuple (as expected)
            _current_position_x, current_position_y = self.current_position

            # calculates the text height from the font scale factor
            # and measures the text width using the underlying rendering
            # infra-structure (avoids possible problems)
            text_height = font_size * FONT_SCALE_FACTOR
            text_height_r = font_size_r * FONT_SCALE_FACTOR
            text_width = self.canvas.stringWidth(text_encoded)

            # initializes the text x coordinate with the margin defined
            # for the current node (difference of margins)
            text_x = (margin_left - margin_right) * FONT_SCALE_FACTOR

            # calculates the appropriate text position according to the
            # "requested" horizontal text alignment
            if text_align == "left":
                text_x += clip_left
            elif text_align == "right":
                text_x += clip_right - text_width
            elif text_align == "center":
                text_x += (
                    clip_left + int((clip_right - clip_left) / 2) - int(text_width / 2)
                )

            # sets the text y as the current position context y
            # default position for the text is the current position
            text_y = clip_top + current_position_y - text_height_r
            text_y = self.ensure_y(text_y, offset=text_height)

            # updates the fill color to a white color and then uses
            # this color to draw a white (background) rectangle around
            # the area that is going to be filled with the text
            self.canvas.setFillColorRGB(1.0, 1.0, 1.0)
            self.canvas.rect(
                text_x,
                text_y - (font_size - font_size_r),
                text_width,
                text_height,
                stroke=0,
                fill=1,
            )

            # "resets" the fill color of the current canvas context to
            # the black color so that it's possible to draw the text with
            # the expected color values as defined in specification
            self.canvas.setFillColorRGB(0, 0, 0)

            # sets the complete computed font in the current canvas context
            # note that the leading value is overridden to avoid font sizing
            # problems in accordance with the printing language specification,
            # the font must be set after the ensure vertical operation so that
            # in case a new page is created the new font is set correctly in it
            self.canvas.setFont(font_name_c, font_size_r, leading=1.0)

            # draws the text string at the calculated position the text
            # is encoded in the expected encoding so that no encoding
            # problems occur (as expected)
            self.canvas.drawString(text_x, text_y, text_encoded)

            # in case the current text height is bigger than the current
            # context biggest height, updates the information
            biggest_height = self.get_context("biggest_height")
            if biggest_height < text_height:
                self.put_context("biggest_height", text_height)

        # in case it's the second visit
        elif self.visit_index == 1:
            # removes the context information
            self.remove_context(node)

    @visited(Image)
    def visit_image(self, node):
        import reportlab.lib.utils

        if self.visit_index == 0:
            # adds the node as the context information
            self.add_context(node)

            # sets the default values for both the image path
            # and source, both values are unset by default
            image_path = None
            image_source = None

            # retrieves the path or source value to be used
            # in the retrieval (only one value is set)
            if self.has_context("path"):
                image_path = self.get_context("path")
            elif self.has_context("source"):
                image_source = self.get_context("source")

            # retrieves the complete set of attributes for the current
            # context to be used for the processing of the node
            text_align = self.get_context("text_align")
            position_x = int(self.get_context("x", "0"))
            position_y = int(self.get_context("y", "0"))
            block_width = int(self.get_context("width", "0"))
            block_height = int(self.get_context("height", "0"))

            # converts the various block related values from their original
            # twip based value into the PDF point value to be used in print
            position_x = int(position_x * TWIP_SCALE * SCALE)
            position_y = int(position_y * TWIP_SCALE * SCALE)
            block_width = int(block_width * TWIP_SCALE * SCALE)
            block_height = int(block_height * TWIP_SCALE * SCALE)

            # verifies if the current context is of type block, so that
            # the proper absolute positions are going to be used instead
            is_block = not block_width == 0 and not block_height == 0

            # sets the initial clip (box) value that will be applied in
            # case the current execution mode is not block based
            clip_left = 0
            clip_top = 0
            clip_right = self.width
            _clip_bottom = self.height

            # verifies if the current mode is block and if that's the case
            # re-calculates the new clip (box) value taking that into account
            if is_block:
                self.single = True
                clip_left = position_x
                clip_top = position_y * -1
                clip_right = position_x + block_width
                _clip_bottom = (position_y + block_height) * -1

            # in case the image path is defined must load the
            # image data from the file system
            if image_path:
                # opens the bitmap image directly from the current
                # file system, no dynamically loaded image
                bitmap_image = PIL.Image.open(image_path)

            # in case the image source is defined must load the
            # base 64 image data from the attribute
            elif image_source:
                # decodes the image source from the default base 64
                # encoding to be used for the loading
                image_source_decoded = base64.b64decode(image_source)

                # creates the image buffer then writes the decoded
                # image into it and opens the file object with the
                # created buffer (image loading into structure)
                image_source_buffer = appier.legacy.BytesIO()
                image_source_buffer.write(image_source_decoded)
                image_source_buffer.seek(0)
                bitmap_image = PIL.Image.open(image_source_buffer)

            # retrieves the bitmap image width and height
            bitmap_image_width, bitmap_image_height = bitmap_image.size

            # creates a new image without transparency settings, so that
            # no extra color is used ands copies the bitmap image into it
            other_image = PIL.Image.new(
                "RGB", (bitmap_image_width, bitmap_image_height), color="white"
            )
            other_image.paste(bitmap_image, bitmap_image)

            # retrieves the current position in x and y unpacking the values
            # from the current position tuple
            _current_position_x, current_position_y = self.current_position

            # calculates the appropriate bitmap position according to the
            # "requested" horizontal text alignment
            if text_align == "left":
                real_bitmap_x = clip_left
            elif text_align == "right":
                real_bitmap_x = clip_right - bitmap_image_width * IMAGE_SCALE_FACTOR
            elif text_align == "center":
                real_bitmap_x = (
                    clip_left
                    + int((clip_right - clip_left) / 2)
                    - int(bitmap_image_width * IMAGE_SCALE_FACTOR / 2)
                )

            # calculates the real bitmap vertical position from the current
            # vertical position minus the height of the image and ensures the
            # position, recalculating a new y position in case the page overflows
            real_bitmap_y = (
                clip_top
                + current_position_y
                - (bitmap_image_height * IMAGE_SCALE_FACTOR)
            )
            real_bitmap_y = self.ensure_y(
                real_bitmap_y, offset=bitmap_image_height * IMAGE_SCALE_FACTOR
            )

            # loads the image image using the proper image reader structure
            # and uses the structure to "draw" the image into the canvas at
            # the current position
            image_reader = reportlab.lib.utils.ImageReader(other_image)
            self.canvas.drawImage(
                image_reader,
                real_bitmap_x,
                real_bitmap_y,
                bitmap_image_width * IMAGE_SCALE_FACTOR,
                bitmap_image_height * IMAGE_SCALE_FACTOR,
            )

            # in case the current image height is bigger than the current
            # context biggest height, updates the information
            biggest_height = self.get_context("biggest_height")
            if biggest_height < bitmap_image_height * IMAGE_SCALE_FACTOR:
                self.put_context(
                    "biggest_height", bitmap_image_height * IMAGE_SCALE_FACTOR
                )

        elif self.visit_index == 1:
            self.remove_context(node)

    def ensure_y(self, y_position, offset):
        """
        Ensures that the provided vertical position is valid for
        the current page (no overflow) in case it's not a new page
        is created and the returned position is the new one.

        The calculation of the new vertical position takes into
        account the provided offset value.

        :type y_position: float
        :param y_position: The vertical position as a PDF point value
        to be validated against the current page metrics.
        :type offset: float
        :param offset: The vertical offset to be applied to the new's
        page vertical value in case a new page is created.
        :rtype: float
        :return: The resulting vertical position taking into account
        creation of new pages.
        """

        # in case the current document in parsing has been marked
        # as single page oriented (absolute positioning), there's
        # no need to verify for new page creation
        if self.single:
            return y_position

        # verifies if the current vertical position "overflows"
        # the page value (lower than zero) in case it does not
        # returns immediately with the provided position (no
        # overflow has occurred)
        b_position = y_position - offset
        if b_position >= 0.0:
            return y_position

        # calculates the delta position (inside the new page)
        # according to the current y position in case it's positive
        # it should be ignored otherwise uses it as the offset
        d_position = 0.0 if y_position >= 0.0 else y_position

        # updates the current position with the initial top left
        # corner position of the new page and update the vertical
        # position coordinate with the offset value and the bottom
        # position (used as an offset)
        self.current_position = (0, self.height + d_position)
        y_position = self.height + d_position - offset

        # shows a new page in the current canvas (creating a new
        # page) and then returns the new vertical position to the
        # caller method
        self.canvas.showPage()
        return y_position

    def ensure_font(self, font_name, file_path=None):
        """
        Ensures that the font is present in the current
        canvas object, loading it into the PDF context
        in case it's required.

        The provided file path may be an absolute path
        or a relative (file name) to the system's default
        font directory.

        :type font_name: String
        :param font_name: The name of the font to be ensured
        to be loaded in the current context.
        :type file_path: String
        :param file_path: The path to the true type font file
        that should be loaded for the font (may be a relative
        or absolute path)
        """

        import reportlab.pdfbase.ttfonts
        import reportlab.pdfbase.pdfmetrics

        # in case the font is already present in the fonts
        # map it's considered to be loaded and so the control
        # must be returned immediately
        if font_name in self.fonts:
            return

        # converts the font name into a lower cased version and
        # then uses it to create the default font path in case
        # none is provided (uses the default true type extension)
        font_name_l = font_name.lower()
        file_path = file_path or font_name_l + ".ttf"

        # sets the error flag as true by default the loading of
        # the font is not possible in case one of the steps
        # completes the error flag is unset
        error = True

        # iterates over all the font paths trying to find a path
        # that can correctly load the requested font
        for font_path in FONT_PATHS:
            try:
                # creates the complete font path with the current
                # base path in iteration and the font name in case
                # the font path is empty the default system wide
                # search will be used (varies from system to system)
                file_path_f = font_path + file_path
                file_path_f = os.path.expanduser(file_path_f)

                # creates the font structure for the font name and path
                # and the registers it in the the current report lab
                # metrics (to be used in further operations)
                font = reportlab.pdfbase.ttfonts.TTFont(font_name, file_path_f)
                reportlab.pdfbase.pdfmetrics.registerFont(font)
            except Exception:
                continue
            else:
                error = False
                break

        # in case the error flag is set raises the invalid font
        # exception, indicating that it was not possible to load
        # the associated font file
        if error:
            raise exceptions.InvalidFont(
                "not possible to load '%s' - '%s'" % (font_name, file_path)
            )

        # updates the fonts map so that the current font is associated
        # with the corresponding loaded file path, this marks the
        # font as loaded for the current context
        self.fonts[font_name] = file_path

    def get_current_position_context(self):
        """
        Retrieves the current position based on the current
        context information.

        :rtype: Tuple
        :return: The current position base on the current context information
        and applied with the font scale factor.
        """

        # retrieves the current position in x and y
        current_position_x, current_position_y = self.current_position

        # converts the current position to context
        current_position_context = (
            FONT_SCALE_FACTOR * current_position_x,
            -1 * FONT_SCALE_FACTOR * current_position_y,
        )

        # returns the current position context
        return current_position_context

    def get_context(self, context_name, default=None):
        if not self.has_context(context_name):
            if not default == None:
                return default
            raise exceptions.InvalidContextInformationName(
                "the context information name: " + context_name + " is invalid"
            )

        return self.peek_context(context_name)

    def add_context(self, node):
        valid_attributes = [
            (value, getattr(node, value))
            for value in dir(node)
            if not value in EXCLUSION_LIST
        ]

        for valid_attribute_name, valid_attribute_value in valid_attributes:
            self.push_context(valid_attribute_name, valid_attribute_value)

    def remove_context(self, node):
        valid_attribute_names = [
            value for value in dir(node) if not value in EXCLUSION_LIST
        ]

        for valid_attribute_name in valid_attribute_names:
            self.pop_context(valid_attribute_name)

    def push_context(self, context_name, context_value):
        if not context_name in self.context_map:
            self.context_map[context_name] = []

        self.context_map[context_name].append(context_value)

    def pop_context(self, context_name):
        if not context_name in self.context_map:
            raise exceptions.InvalidContextInformationName(
                "the context information name: " + context_name + " is invalid"
            )

        self.context_map[context_name].pop()

    def peek_context(self, context_name):
        if not context_name in self.context_map:
            raise exceptions.InvalidContextInformationName(
                "the context information name: " + context_name + " is invalid"
            )

        return self.context_map[context_name][-1]

    def put_context(self, context_name, context_value):
        """
        Puts the given context information in the context
        information map.

        :type context_name: String
        :param context_name: The name of the context information
        to be put in the context information map.
        :type context_value: Object
        :param context_value: The value of the context information to be put
        in the context information map.
        """

        if not context_name in self.context_map:
            raise exceptions.InvalidContextInformationName(
                "the context information name: " + context_name + " is invalid"
            )

        self.context_map[context_name][-1] = context_value

    def has_context(self, context_name):
        """
        Tests if the given context information name exists
        in the current context information map.

        :type context_name: String
        :param context_name: The context information name
        to be tested against the current context information map.
        :rtype: bool
        :return: If the context information name exists in the
        current context information map (and is valid).
        """

        # in case the context information name exists in the
        # context information map and is not invalid
        if context_name in self.context_map and self.context_map[context_name]:
            return True
        else:
            return False
