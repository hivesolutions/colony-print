# Binie File Format Specification 1.1

## Motivation

Binie is a binary file format specification crafted to enable consistent and structured representation of documents, particularly for print media.
It is engineered to support diverse document layouts, allowing various applications to create and interpret Binie-compliant documents reliably. Binie achieves this by defining a clear, extensible structure for document components, including text and images.
This approach ensures that a single document file can be used across different platforms and applications, maintaining its layout integrity and visual fidelity.

## Specification

The Binie file consists of a document header followed by a series of elements. Each element can be either text or an image, each with its specific header and data.

Every integer in the Binie specification is encoded in Little Endian format.

### Binie Header

Binie documents begin with a standard header that includes essential metadata about the document:

| Offset (bytes) | Length (bytes) | Content         |
| -------------- | -------------- | --------------- |
| 0              | 256            | Document title  |
| 256            | 4              | Document width  |
| 260            | 4              | Document height |
| 264            | 4              | Element count   |

### Element Header

Following the header, Binie documents contain a series of elements, each with a defined structure.
Each element in the document (text or image) starts with a standard header.

| Offset (from element start) | Length (bytes) | Content                                        |
| --------------------------- | -------------- | ---------------------------------------------- |
| 0                           | 4              | Element type (eg: `1` for text, `2` for image) |
| 4                           | 4              | Element data length                            |

### Text Element

Text elements have their specific header followed by the actual text.
The element type for text elements is identified by the value `1`.

#### Text Element Header

| Offset (from text element start) | Length (bytes) | Content       |
| -------------------------------- | -------------- | ------------- |
| 0                                | 8              | Common header |
| 8                                | 8              | Position      |
| 16                               | 256            | Font          |
| 272                              | 4              | Font size     |
| 276                              | 4              | Text align    |
| 280                              | 4              | Text weight   |
| 284                              | 4              | Text italic   |
| 288                              | 4              | Margin left   |
| 292                              | 4              | Margin right  |
| 296                              | 4              | Position X    |
| 300                              | 4              | Position Y    |
| 304                              | 4              | Block width   |
| 308                              | 4              | Block height  |
| 312                              | 4              | Data Length   |

#### Text Data

Follows immediately after the text element header and contains the context specific payload of the text - typically the text itself.
The text is encoded in UTF-8 and ends with a null byte, that is counted by the text data length.

#### Text Extension

The text data may be followed by an extension with additional properties of the text.
The extension is present when the element data length leaves room for its fields (8 bytes) after the text element header (without the common header) and the text data, and producers only add it when one of its properties is set.
A shorter remainder is not an extension and is ignored, as are the bytes after the fields of the extension, that future versions may use (keeping the last byte of the element zero).

| Offset (from extension start) | Length (bytes) | Content    |
| ----------------------------- | -------------- | ---------- |
| 0                             | 4              | Text flags |
| 4                             | 4              | Reserved   |

The reserved value must be zero, so that the last byte of the element is always zero, as the renderers released before the extension expect a text element to end with the null terminator of its text.

#### Text Flags

The text flags are a bit mask, renderers must ignore the flags they don't know.

| Text Flag | Value    | Description                                                                                                      |
| --------- | -------- | ---------------------------------------------------------------------------------------------------------------- |
| Wrap      | `0x0001` | The text is wrapped into as many lines as needed to fit the available width, see [Text Wrapping](#text-wrapping) |

### Image Element

Image elements contain image data.
The element type for image elements is identified by the value `2`.

#### Image Element Header

| Offset (from image element start) | Length (bytes) | Content       |
| --------------------------------- | -------------- | ------------- |
| 0                                 | 8              | Common header |
| 8                                 | 8              | Position      |
| 16                                | 4              | Text align    |
| 20                                | 4              | Position X    |
| 24                                | 4              | Position Y    |
| 28                                | 4              | Block width   |
| 32                                | 4              | Block height  |
| 36                                | 4              | Data Length   |

#### Image Data

Follows immediately after the image element header that contains the binary contents of the image itself.

### Text Alignment

Text alignment within the elements is specified using alignment values:

| Text Alignment   | Value |
| ---------------- | ----- |
| Left alignment   | 1     |
| Right alignment  | 2     |
| Center alignment | 3     |

### Text Wrapping

A text without the wrap flag is drawn in a single line, even when it goes beyond the available width (and is cut by the edges of the paper).
A text with the wrap flag is laid out in as many lines as needed, following the same rules in every renderer, so that a document prints the same way on every system:

* The available width is the width of the printable area, or of the block when the text is inside one, minus the left and right margins of the text (in points, 20 twips each). When it's not positive, the text is drawn in a single line, as if it had no wrap flag.
* Lines are broken at spaces (the U+0020 character only, never at a tab nor at a no-break space such as U+00A0 or U+202F), each line taking as many words as fit in the available width, measured with the font of the text, and the spaces where a line is broken (all of them, when there are several) and the ones before a line feed are not drawn nor measured. A word wider than the available width is broken between characters (the Unicode code points of the text, never splitting the bytes of a character nor a UTF-16 surrogate pair), each line taking at least one character, so that no text is lost. A line feed (`\n`) always starts a new line.
* Each line is aligned according to the text alignment of the element inside of the available width (a left aligned line starts at the left margin, a right aligned one ends at the right margin and a centered one is centered between them), the first one at the position of the element (its `Position` field) and each next one a text height below the previous one, the font size times 20 twips (the height producers give to the lines of text). As the texts without the wrap flag are moved by the difference of their margins instead, a wrapped left aligned text with a right margin, a right aligned one with a left margin or a centered one with different margins may be drawn at another position than without the flag. Every line goes through the page break rules of the renderer, as any other text, and the lines after the first one of the wrapped texts of a line are drawn after the other elements of the line, from top to bottom (the second lines of all of them, in the order of their elements, before the third ones, and so on), so that a page break they cause never moves the elements of their line nor the lines above it.
* The elements of the same line (the ones with the same vertical position, the second value of the `Position` field, outside of blocks) keep their position, and the elements of the following lines are moved down by `max(0, H - h)`, where `H` is the largest height of the wrapped texts of the line (the number of lines times the font size times 20 twips) and `h` is the height of the line before the wrapping, the one of its tallest element (the font size times 20 twips for the texts and the height of the bitmap in pixels times 10 twips for the images), so that a wrapped text that fits in a single line (or beside a taller element) moves nothing, the moves of the lines adding up. The elements of a line are consecutive in the document, and a line ends at the first element (inside of a block or not) with another vertical position, or at the end of the document for its last line, its move being applied, and the lines after the first one of its wrapped texts drawn, before that element.
* A wrapped text inside a block (with a non zero block width and height) is wrapped to the width of the block and never moves other elements, its lines beyond the height of the block being drawn as they are (not clipped, as the texts that go beyond a block). The elements of blocks are positioned relative to the flow of the lines, so they're moved by the shift that the lines outside of blocks above them have built up, as the following lines are, without being part of those lines (they don't count in `h`).

The wrapping happens in the renderer as it's the only one that knows both the available width (the paper of the printer, for the documents without a size) and the metrics of the fonts, the producers only set the flag.

#### Renderers and PDF

The Binie documents are rendered by the GDI renderer of npcolony (the Windows nodes and the browser plugin) and by the PDF renderer of Colony Print, that replays them into PDF documents with the GDI layout. The PDF renderer is used by the Linux nodes, which convert every Binie document into PDF, whether they print it through CUPS, send it by email or save it as the output of the job (such as the PDF version of a document for a client). The Windows nodes in email mode print through GDI to a PDF printer. Both renderers follow the rules above, with these consequences for the PDF documents:

* The lines are measured with the font embedded in the PDF document, the same font file the GDI renderer uses when it's installed. The GDI renderer rounds and hints the metrics of the fonts, so in a few cases a line may break one word earlier or later in one of the renderers.
* A wrapped text makes the document taller, so the documents get more pages when their content goes beyond the page, as with any other content.
* The PDF documents printed as they are (the `pdf` format of the nodes) are not affected, as Colony Print doesn't lay them out.

## Validation and Compatibility

The Binie file format is designed to be robust and flexible. Implementations should handle unexpected values gracefully, defaulting to sensible behavior where possible. For example, unknown element types should be ignored, and missing data should be handled without causing crashes or major issues.

The renderers released before the text extension ignore it, as they read the text up to its null terminator, and draw the text in a single line. A document that uses the extension can then be printed by any renderer, the texts with the wrap flag being wrapped only by the ones that support it (the Colony Print nodes with the `text-wrap` capability).

## Future Extensions

The structure of the Binie file format allows for future extensions, such as new element types or additional metadata in headers. Implementations should be designed to accommodate such changes, ensuring backward and forward compatibility.

## Version History

| Version | Changes                                                                                                                    |
| ------- | -------------------------------------------------------------------------------------------------------------------------- |
| 1.0     | Initial version, with the text and image elements                                                                          |
| 1.1     | Text encoded in UTF-8 and ended by a null byte, text extension with the text flags and the wrap flag for the text wrapping |
