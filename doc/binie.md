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
The encoding of the text is not specified and should be handled by the application.

#### Text Extension

The text data may be followed by an extension with additional properties of the text.
The extension is present when the element data length is larger than the size of the text element header (without the common header) plus the text data length, and producers only add it when one of its properties is set.

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

* The available width is the width of the printable area, or of the block when the text is inside one, minus the left and right margins of the text.
* Lines are broken at spaces, each line taking as many words as fit in the available width, measured with the font of the text, and the space where a line is broken is not drawn. A word wider than the available width is broken between characters, so that no text is lost. A line feed (`\n`) always starts a new line.
* Each line is aligned according to the text alignment of the element, the first one at the position of the element and each next one a text height below the previous one, the font size times 20 twips (the height producers give to the lines of text). Every line goes through the page break rules of the renderer, as any other text.
* The lines added by the wrapping move down every element of the following lines of the document by their height. The elements of the same line (the ones with the same vertical position) keep their position, and the line grows by the height of its tallest wrapped text.
* A text inside a block (with a non zero block width and height) is wrapped to the width of the block and clipped by it, it never moves other elements nor is moved by them.

The wrapping happens in the renderer as it's the only one that knows both the available width (the paper of the printer, for the documents without a size) and the metrics of the fonts, the producers only set the flag.

## Validation and Compatibility

The Binie file format is designed to be robust and flexible. Implementations should handle unexpected values gracefully, defaulting to sensible behavior where possible. For example, unknown element types should be ignored, and missing data should be handled without causing crashes or major issues.

The renderers released before the text extension ignore it, as they read the text up to its null terminator, and draw the text in a single line. A document that uses the extension can then be printed by any renderer, the texts with the wrap flag being wrapped only by the ones that support it (the Colony Print nodes with the `text-wrap` capability).

## Future Extensions

The structure of the Binie file format allows for future extensions, such as new element types or additional metadata in headers. Implementations should be designed to accommodate such changes, ensuring backward and forward compatibility.

## Version History

| Version | Changes                                                                     |
| ------- | --------------------------------------------------------------------------- |
| 1.0     | Initial version, with the text and image elements                           |
| 1.1     | Text extension, with the text flags and the wrap flag for the text wrapping |
