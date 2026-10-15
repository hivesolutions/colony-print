# XMPL – XML Markup Language for Printing 1.1

## Motivation

XMPL is a file format specification developed to enable diverse applications to create and manipulate structured documents for printing purposes.
The design of XMPL facilitates its conversion into Binie format, making it a versatile intermediary for rendering structured, print-ready documents.
XMPL appends additional, implementation-agnostic information about the document layout, allowing a single XML-based file to be transformed into a fully-featured, print-ready format.

## Specification

XMPL uses an XML structure where each element and attribute is carefully defined to represent various components of a print document.

### XMPL Document Structure

XML documents are structured with nested elements, each representing a part of the print layout, such as blocks, paragraphs, lines, text, and images.

#### Document Root: `printing_document`

The root element for any XMPL document. It encapsulates all the content elements of the document.
Its `width` and `height` are the size of the document and not the ones of a block, so the texts and images are only inside of a block (aligned, broken into pages and wrapped within it) when inside of a `block` element with its own `width` and `height`.

```xml
<printing_document>
    <!-- Nested Elements -->
</printing_document>
```

#### Block Element: `block`

Defines a box (`x`, `y`, `width` and `height`) that holds text and image elements only, placed relative to the current position of the flow without advancing it.

```xml
<block>
    <!-- Nested Elements -->
</block>
```

#### Paragraph Element: `paragraph`

Represents a paragraph of the document, grouping lines, texts and images.

```xml
<paragraph>
    <!-- Nested Elements -->
</paragraph>
```

#### Line Element: `line`

Denotes a single line within a paragraph, typically holding text or image elements.

```xml
<line>
    <!-- Nested Elements -->
</line>
```

#### Text Element: `text`

Specifies a segment of text within a line or a paragraph.

```xml
<text>
    <!-- Text Content -->
</text>
```

#### Image Element: `image`

Used for embedding images within the document layout.

```xml
<image>
    <!-- Image Attributes -->
</image>
```

The image is either inline, with its base64 encoded data in the `source` attribute, or read from the file system with the `path` attribute. The XMPL documents printed by the nodes (print jobs) only accept inline images, as the paths would be read from the file system of the node.

#### Font Element: `font`

Declares a font used by the document, to be installed on demand by the node that prints the document (with the `dynamic-fonts` capability). Font elements are direct children of the `printing_document` element (they are ignored elsewhere) and are never printed. The nodes without the capability print the document with their own fonts, the declared fonts being skipped.

```xml
<font name="2 of 5" url="https://fonts.example.com/2of5.ttf" />
```

The attributes of the element are the fields of the entries of the fonts of a print request: `name` (the family name of the font, as used by the `font` attributes of the document), `style` (`regular`, `bold`, `italic` or `bold_italic`, read from the font file when omitted) and exactly one of `data_b64` (the base64 encoded TrueType font file) or `url` (the URL of the font file), or `md5` alone (a reference to a font already installed in the node). See [Print Fonts](../README.md#print-fonts) for the complete description.

### Attributes and Properties

Elements in XMPL files may have various attributes defining their properties, such as font for text or size for images.

#### Text Wrapping

The `text_wrap` attribute defines if a text wider than the available width is wrapped into as many lines as needed (`wrap`) or kept in a single line (`nowrap`, the default, also used for any other value).
As the other attributes of the text (such as `text_align` or `font_style`) it can be defined in the `text` element or in one of its parents (`line`, `paragraph`, `block` or `printing_document`), the closest one being used.

```xml
<paragraph text_align="center" text_wrap="wrap">
    <line><text>A long note for the team that prepares the order, wrapped to the width of the paper</text></line>
</paragraph>
```

The wrapped texts are converted into Binie text elements with the wrap flag, that are laid out by the renderer, see [Text Wrapping](binie.md#text-wrapping).
The conversion of XMPL documents straight into PDF documents (`POST /documents.pdf`) applies the same rules from the attribute, wrapping the texts to the width of the page (instead of the printable area of a printer) and measuring them with its own font metrics, so the PDF version of a document wraps its texts as the printed one does when its page has the width of the printable area, a line breaking one word earlier or later in a few cases (as between the renderers, see [Renderers and PDF](binie.md#renderers-and-pdf)).

### Convertibility to Binie

The XMPL format has been designed for easy and efficient conversion to the Binie file format.
This feature allows XMPL to serve as a flexible tool for creating structured documents that can be readily transformed into a print-ready format.
The font elements are not part of the converted Binie document, the fonts they declare are sent with the print job instead.

### Example

Below is an example of an XMPL document designed to display "Hello World" in a centered paragraph.

```xml
<?xml version="1.0" encoding="UTF-8"?>
<printing_document name="hello_world" font="Calibri" font_size="9">
    <paragraph text_align="center">
        <line><text>Hello World</text></line>
    </paragraph>
</printing_document>
```

## Validation and Compatibility

XMPL is structured to be robust and flexible, ensuring that the conversion to Binie maintains the integrity and layout of the document.
Implementations are expected to handle XMPL structure gracefully, supporting a wide range of document configurations.

## Version History

| Version | Changes                                                                                                                                                             |
| ------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1.0     | Initial version                                                                                                                                                     |
| 1.1     | `text_wrap` attribute, converted into the Binie 1.1 wrap flag, and the `width` and `height` of `printing_document` no longer making a block of its texts and images |
