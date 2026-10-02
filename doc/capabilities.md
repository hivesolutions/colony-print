# Colony Print Node Capabilities

## Motivation

Colony Print nodes run on different systems (Windows and Linux), with different engines and versions of their dependencies, so they don't all support the same features. Each node advertises the features it supports as capabilities, so that clients (and the admin UI) know what a node is able to do, and so that the server refuses the requests a node is not able to handle, instead of sending them to the node where they would be silently ignored.

## Specification

### Naming

Capabilities are identified by lowercase, dash separated names (e.g. `dynamic-fonts`, `custom-paper` or `gravo-check-path`), which never change once released.

### Advertising

* Nodes compute their capabilities at runtime, from their engines, their system (and its npcolony version) and their mode, and send them in the `capabilities` list of the node information (`POST /nodes/<id>`), on every iteration of their loop.
* The server keeps the node information and returns it, together with the capabilities, in `GET /nodes` and `GET /nodes/<id>`.
* The requests that use a feature that requires a capability fail with `409` when the node doesn't advertise it, naming the missing capability. This includes unknown nodes and nodes released before the capabilities, that advertise none. The fonts of the print jobs are the exception, as they're skipped for the nodes without the `dynamic-fonts` capability, that print the documents with their own fonts.
* Nodes also verify the jobs they receive and fail the ones that require a capability they don't support (e.g. a job queued before the node restarted with an older npcolony).

The features that existed before the capabilities (the engines, the formats, the email mode and the gravo payload fields) are advertised but not verified by the server, as older nodes support them without advertising them.

### Capabilities

| Capability                                              | Description                                                                                                                  | Advertised when                                                                                                   | Enables                                                                                                     |
| ------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `npcolony`, `gravo`, `text`                             | The engine is available in the node, the same as the `engines` of the node information.                                      | The engine is available.                                                                                          | The `type` of the print request.                                                                            |
| `binie`                                                 | Prints Binie documents, on Windows through GDI and on Linux converting them into PDF documents with the GDI layout.          | The npcolony engine is available.                                                                                 | The `binie` format.                                                                                         |
| `pdf`                                                   | Prints PDF documents as they are.                                                                                            | The npcolony engine prints PDF documents (Linux).                                                                 | The `pdf` format.                                                                                           |
| `custom-paper`                                          | Binie documents use their own size as a custom paper size when the printer accepts it, as the Windows printer drivers do.    | Windows, or Linux with an npcolony that reports the custom paper sizes of the printers.                           | -                                                                                                           |
| `email`                                                 | Prints the documents into PDF documents that are sent by email, instead of printing them.                                    | The node runs in the `email` mode (`NODE_MODE=email`).                                                            | The `save_output` and `email_*` options.                                                                    |
| `gravo-extra-fonts`, `gravo-record`, `gravo-check-path` | Optional fields of the gravo print payload.                                                                                  | The gravo engine is available.                                                                                    | The `extra_fonts`, `record` and `check_path` fields of the gravo print payload.                             |
| `xmpl`                                                  | Prints XMPL documents, converting them into Binie documents in the node (with the fonts they declare).                       | The npcolony engine is available.                                                                                 | The `xmpl` format (verified by the server).                                                                 |
| `dynamic-fonts`                                         | Installs the fonts sent with the print jobs on demand, keeping them in a cache of the node by URL and MD5, and reports them. | Linux nodes (fonts embedded in the PDF documents), Windows nodes whose npcolony reports the `load-fonts` feature. | The `fonts` field and the fonts declared by XMPL documents (skipped otherwise) and the fonts of the node (verified by the server). |

The `fonts` field and the fonts endpoints of the nodes (`GET` and `POST /nodes/<id>/fonts`) are described in [Print Fonts](../README.md#print-fonts), and the font elements of XMPL documents in the [XMPL Specification](xmpl.md).

### Example

The node information of a Linux node with the npcolony engine, as sent to the server:

```json
{
  "name": "store",
  "mode": "normal",
  "printer": "default",
  "engines": ["npcolony", "text"],
  "capabilities": [
    "npcolony",
    "text",
    "binie",
    "xmpl",
    "pdf",
    "custom-paper",
    "dynamic-fonts"
  ],
  "fonts": [
    {
      "name": "2 of 5",
      "style": "regular",
      "md5": "9e107d9d372bb6826bd81d3542a419d6",
      "url": "https://fonts.example.com/2of5.ttf",
      "size": 18496,
      "time": 1790879619.9,
      "active": true
    }
  ],
  "platform": "linux",
  "version": "0.20.0"
}
```
