# Binie File Format Specification 1.0

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

| Offset (from text element start) | Length (bytes) | Content             |
| -------------------------------- | -------------- | ------------------- |
| 0                                | 8              | Common header       |
| 8                                | 8              | Position            |
| 16                               | 256            | Font                |
| ...                              | ...            | Additional settings |

#### Text Data

Follows immediately after the text element header and contains the context specific payload of the text - typically the text itself.

### Image Element

Image elements contain image data.
The element type for image elements is identified by the value `2`.

#### Image Element Header

| Offset (from image element start) | Length (bytes) | Content        |
| --------------------------------- | -------------- | -------------- |
| 0                                 | 8              | Common header  |
| 8                                 | 8              | Position       |
| 16                                | 4              | Text align     |
| 20                                | 4              | Position X     |
| 24                                | 4              | Position Y     |
| 28                                | 4              | Block width    |
| 32                                | 4              | Block height   |
| 36                                | 4              | Length of data |

#### Image Data

Follows immediately after the image element header that contains the binary contents of the image itself.

### Text Alignment

Text alignment within the elements is specified using alignment values:

| Text Alignment   | Value |
| ---------------- | ----- |
| Left alignment   | 1     |
| Right alignment  | 2     |
| Center alignment | 3     |

## Validation and Compatibility

The Binie file format is designed to be robust and flexible. Implementations should handle unexpected values gracefully, defaulting to sensible behavior where possible. For example, unknown element types should be ignored, and missing data should be handled without causing crashes or major issues.

## Future Extensions

The structure of the Binie file format allows for future extensions, such as new element types or additional metadata in headers. Implementations should be designed to accommodate such changes, ensuring backward and forward compatibility.
