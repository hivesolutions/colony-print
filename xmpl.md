# XMPL – XML Markup Language for Printing 1.0

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

```xml
<printing_document>
    <!-- Nested Elements -->
</printing_document>
```

#### Block Element: `block`

Defines a container for grouping related content elements like paragraphs, text, and images.

```xml
<block>
    <!-- Nested Elements -->
</block>
```

#### Paragraph Element: `paragraph`

Represents a paragraph within a block, including lines, text, or images.

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

### Attributes and Properties

Elements in XMPL files may have various attributes defining their properties, such as font for text or size for images.

### Convertibility to Binie

The XMPL format has been designed for easy and efficient conversion to the Binie file format. 
This feature allows XMPL to serve as a flexible tool for creating structured documents that can be readily transformed into a print-ready format.

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
