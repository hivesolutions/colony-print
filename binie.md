# Binie File Format Specification 1.0

## Motivation

Binie is a binary file format specification crafted to enable consistent and structured representation of documents, particularly for print media. 
It is engineered to support diverse document layouts, allowing various applications to create and interpret Binie-compliant documents reliably. Binie achieves this by defining a clear, extensible structure for document components, including text and images. 
This approach ensures that a single document file can be used across different platforms and applications, maintaining its layout integrity and visual fidelity.

## Specification

Every integer in the Binie specification is encoded in Little Endian format.

### Binie Header

Binie documents begin with a standard header that includes essential metadata about the document:

| Offset | Content                               |
|--------|---------------------------------------|
| 0      | Document title (256 bytes)            |
| 256    | Document width (4 bytes)              |
| 260    | Document height (4 bytes)             |
| 264    | Element count (4 bytes)               |

### Binie Elements

Following the header, Binie documents contain a series of elements, each with a defined structure.

#### Element Header

Each element, whether text or image, starts with a header:

| Offset | Content                               |
|--------|---------------------------------------|
| 0      | Element type (4 bytes)                |
| 4      | Element data length (4 bytes)         |

#### Text Elements

Text elements are structured to include font and alignment details:

| Offset | Content                               |
|--------|---------------------------------------|
| 0      | Text Element Header                   |
| ...    | Text Data                             |

##### Text Element Header

The header for a text element contains:

| Offset | Content                               |
|--------|---------------------------------------|
| 0      | Position (X, Y - 4 bytes each)        |
| 8      | Font name (256 bytes)                 |
| 264    | Font size (4 bytes)                   |
| 268    | Text alignment (4 bytes)              |

#### Image Elements

Image elements are formatted to specify layout and size:

| Offset | Content                               |
|--------|---------------------------------------|
| 0      | Image Element Header                  |
| ...    | Image Data                            |

##### Image Element Header

The header for an image element includes:

| Offset | Content                               |
|--------|---------------------------------------|
| 0      | Position (X, Y - 4 bytes each)        |
| ...    | Additional settings                   |

### Constants and Element Types

Binie specifies constants for element types and alignments to standardize document structure.

| Name                        | Value | Description                    |
|-----------------------------|-------|--------------------------------|
| `TEXT_VALUE`                | 1     | Identifier for text elements   |
| `IMAGE_VALUE`               | 2     | Identifier for image elements  |
| `LEFT_TEXT_ALIGN_VALUE`     | 1     | Left text alignment            |
| `RIGHT_TEXT_ALIGN_VALUE`    | 2     | Right text alignment           |
| `CENTER_TEXT_ALIGN_VALUE`   | 3     | Center text alignment          |

## Validation and Compatibility

Binie's design emphasizes robustness and adaptability. Implementations should gracefully handle unexpected content, prioritizing document integrity and readability. The specification anticipates future enhancements, ensuring that Binie documents remain compatible across different versions and implementations.

## Future Extensions

The Binie file format, with its modular design, is well-suited for future expansions. New element types or additional metadata fields can be seamlessly integrated, fostering an evolving standard that adapts to emerging requirements in document representation and printing technology.
