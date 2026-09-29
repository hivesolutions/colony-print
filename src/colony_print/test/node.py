#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import re
import sys
import json
import base64
import shutil
import struct
import tempfile
import unittest

import appier

import colony_print.node

FONTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "assets", "fonts"
)
""" The path to the directory that contains the fonts bundled
with the repository, used by the binie documents of the tests """

RECEIPT_DEVICE = dict(
    name="Receipt",
    is_default=False,
    media="RP80x297",
    width=226.77,
    length=841.89,
    left=11.34,
    bottom=0.0,
    right=215.43,
    top=841.89,
)
""" The device of an 80 mm receipt printer, as reported by npcolony
for a CUPS queue (sizes in points, printable area 72 mm wide) """

OFFICE_DEVICE = dict(
    name="office",
    is_default=True,
    media="A4",
    width=595.28,
    length=841.89,
    left=12.0,
    bottom=12.0,
    right=583.28,
    top=829.89,
)
""" The device of an A4 office printer (the default printer), as
reported by npcolony for a CUPS queue (sizes in points) """


class MockGravostyleAPI(object):
    """
    Stand-in for gravo pilot's GravostyleAPI that records the keyword
    arguments passed to write_text, so that the flag forwarding done by
    the node can be inspected without driving the real software.
    """

    calls = []

    def write_text(self, text, **kwargs):
        MockGravostyleAPI.calls.append(kwargs)
        return []


class MockGravoPilot(object):
    """
    Stand-in for the gravo pilot module that exposes the minimal
    surface used by the node, namely the GravostyleAPI class and the
    capture_logs context manager, so that _handle_gravo can be
    exercised without the real dependency installed.
    """

    GravostyleAPI = MockGravostyleAPI

    @staticmethod
    def capture_logs(*args, **kwargs):
        import contextlib

        @contextlib.contextmanager
        def _capture():
            yield []

        return _capture()


class MockNPColony(object):
    """
    Stand-in for the npcolony module that exposes a configurable format
    and set of devices and records the documents sent for printing, so
    that the conversion of binie documents done by the node for the PDF
    (CUPS) systems can be exercised without printers.
    """

    format = "pdf"
    devices = []
    calls = []

    @staticmethod
    def get_format():
        return MockNPColony.format

    @staticmethod
    def get_devices():
        return MockNPColony.devices

    @staticmethod
    def print_printer_base64(printer, data_b64, options=None):
        options = options or dict()
        MockNPColony.calls.append((printer, data_b64, dict(options)))
        output_path = options.get("output_path", None)
        if output_path:
            with open(output_path, "wb") as file:
                file.write(base64.b64decode(data_b64))
        return 0

    @staticmethod
    def print_base64(data_b64):
        MockNPColony.calls.append((None, data_b64, dict()))


class MockNPColonyLegacy(object):
    """
    Stand-in for a legacy version of the npcolony module that is not
    able to report the format of the documents it prints.
    """

    @staticmethod
    def print_base64(data_b64):
        pass


class ColonyPrintNodeTest(unittest.TestCase):
    def setUp(self):
        self.node = colony_print.node.ColonyPrintNode()
        self.target_dir = tempfile.mkdtemp(prefix="colony-print-fonts-test-")
        MockGravostyleAPI.calls = []
        self._gravo_pilot = sys.modules.get("gravo_pilot")
        sys.modules["gravo_pilot"] = MockGravoPilot
        MockNPColony.format = "pdf"
        MockNPColony.devices = [RECEIPT_DEVICE, OFFICE_DEVICE]
        MockNPColony.calls = []
        self._npcolony = sys.modules.get("npcolony")
        sys.modules["npcolony"] = MockNPColony
        self._font_paths = colony_print.printing.pdf.visitor.FONT_PATHS
        colony_print.printing.pdf.visitor.FONT_PATHS = (os.path.join(FONTS_PATH, ""),)

    def tearDown(self):
        shutil.rmtree(self.target_dir, ignore_errors=True)
        if self._gravo_pilot == None:
            sys.modules.pop("gravo_pilot", None)
        else:
            sys.modules["gravo_pilot"] = self._gravo_pilot
        if self._npcolony == None:
            sys.modules.pop("npcolony", None)
        else:
            sys.modules["npcolony"] = self._npcolony
        colony_print.printing.pdf.visitor.FONT_PATHS = self._font_paths

    def _gravo_payload(self, **kwargs):
        data = dict(text="Hello World")
        data.update(kwargs)
        return base64.b64encode(json.dumps(data).encode("utf-8"))

    def _media_box(self, data_b64):
        data = base64.b64decode(data_b64)
        pattern = b"/MediaBox \\[ (\\S+) (\\S+) (\\S+) (\\S+) \\]"
        return tuple(float(value) for value in re.search(pattern, data).groups())

    def test_print_job_email_binie(self):
        self.node.node_printer = "Receipt"
        self.node.node_email_receivers = []
        result = self.node.print_job_email(
            dict(
                data_b64=colony_print.controllers.node.HELLO_WORLD_B64,
                name="hello_world",
                format="binie",
                options=dict(save_output=True, send_email=False),
            )
        )
        self.assertEqual(result["result"], "success")
        self.assertEqual(result["output_mime_type"], "application/pdf")
        self.assertEqual(base64.b64decode(result["output_data"])[:5], b"%PDF-")

        printer, data_b64, options = MockNPColony.calls[0]
        self.assertEqual(printer, "Receipt")
        self.assertEqual(options["media"], "RP80x297")
        self.assertEqual(options["scaling"], "none")
        self.assertEqual(options["output_path"].endswith(".pdf"), True)
        self.assertEqual(
            base64.b64decode(data_b64), base64.b64decode(result["output_data"])
        )

    def test_handle_job_title(self):
        data_b64 = base64.b64encode(b"%PDF-1.4 document").decode("utf-8")
        result = self.node._handle_job(
            dict(data_b64=data_b64, name="invoice", printer="office", format="pdf")
        )
        self.assertEqual(
            result,
            dict(result="success", handler="npcolony", printer="office", data=dict()),
        )
        self.assertEqual(
            MockNPColony.calls, [("office", data_b64, dict(title="invoice"))]
        )

    def test_handle_npcolony_binie(self):
        self.node._handle_npcolony(
            colony_print.controllers.node.HELLO_WORLD_B64,
            format="binie",
            printer="Receipt",
            options=dict(title="hello_world"),
        )
        printer, data_b64, options = MockNPColony.calls[0]
        self.assertEqual(printer, "Receipt")
        self.assertEqual(base64.b64decode(data_b64)[:5], b"%PDF-")
        self.assertEqual(
            options, dict(title="hello_world", media="RP80x297", scaling="none")
        )
        self.assertEqual(self._media_box(data_b64), (0.0, 0.0, 226.77, 841.89))

    def test_handle_npcolony_binie_detected(self):
        self.node._handle_npcolony(
            colony_print.controllers.node.HELLO_WORLD_B64, printer="default"
        )
        printer, data_b64, options = MockNPColony.calls[0]
        self.assertEqual(printer, "default")
        self.assertEqual(base64.b64decode(data_b64)[:5], b"%PDF-")
        self.assertEqual(options, dict(media="A4", scaling="none"))
        self.assertEqual(self._media_box(data_b64), (0.0, 0.0, 595.28, 841.89))

    def test_handle_npcolony_default(self):
        self.node._handle_npcolony(
            colony_print.controllers.node.HELLO_WORLD_B64, format="binie"
        )
        printer, data_b64, options = MockNPColony.calls[0]
        self.assertEqual(printer, None)
        self.assertEqual(base64.b64decode(data_b64)[:5], b"%PDF-")
        self.assertEqual(options, dict())

    def test_handle_npcolony_pdf(self):
        data_b64 = base64.b64encode(b"%PDF-1.4 document").decode("utf-8")
        self.node._handle_npcolony(
            data_b64,
            format="pdf",
            printer="Receipt",
            options=dict(media="Custom.80x200mm", scaling="fit"),
        )
        self.assertEqual(
            MockNPColony.calls,
            [("Receipt", data_b64, dict(media="Custom.80x200mm", scaling="fit"))],
        )

    def test_handle_npcolony_raw(self):
        data_b64 = base64.b64encode(b"raw printer data").decode("utf-8")
        self.node._handle_npcolony(data_b64, printer="Receipt")
        self.assertEqual(MockNPColony.calls, [("Receipt", data_b64, dict())])

    def test_handle_npcolony_binie_system(self):
        MockNPColony.format = "binie"
        self.node._handle_npcolony(
            colony_print.controllers.node.HELLO_WORLD_B64,
            format="binie",
            printer="Receipt",
        )
        self.assertEqual(
            MockNPColony.calls,
            [("Receipt", colony_print.controllers.node.HELLO_WORLD_B64, dict())],
        )

    def test_handle_npcolony_invalid_format(self):
        self.assertRaises(
            appier.OperationalError,
            lambda: self.node._handle_npcolony(
                colony_print.controllers.node.HELLO_WORLD_B64,
                format="zpl",
                printer="Receipt",
            ),
        )
        self.assertEqual(MockNPColony.calls, [])

    def test_is_binie(self):
        binie_b64 = colony_print.controllers.node.HELLO_WORLD_B64
        pdf_b64 = base64.b64encode(b"%PDF-1.4 document").decode("utf-8")
        self.assertEqual(self.node._is_binie(binie_b64), True)
        self.assertEqual(self.node._is_binie(binie_b64, format="binie"), True)
        self.assertEqual(self.node._is_binie(binie_b64, format="pdf"), False)
        self.assertEqual(self.node._is_binie(pdf_b64), False)
        self.assertEqual(self.node._is_binie(pdf_b64, format="binie"), True)
        self.assertEqual(self.node._is_binie("not base64 data"), False)

        data = base64.b64decode(binie_b64)
        data = data[:264] + struct.pack("<I", 2) + data[268:] + struct.pack("<II", 3, 0)
        self.assertEqual(
            self.node._is_binie(base64.b64encode(data).decode("utf-8")), True
        )

        MockNPColony.format = "binie"
        self.assertEqual(self.node._is_binie(binie_b64), False)
        self.assertEqual(self.node._is_binie(binie_b64, format="binie"), False)

        sys.modules["npcolony"] = MockNPColonyLegacy
        self.assertEqual(self.node._is_binie(binie_b64, format="binie"), False)

    def test_convert_binie(self):
        data_b64, options = self.node._convert_binie(
            colony_print.controllers.node.HELLO_WORLD_B64,
            printer="receipt",
            options=dict(title="hello_world", media="Custom.80x200mm", scaling="fit"),
        )
        self.assertEqual(base64.b64decode(data_b64)[:5], b"%PDF-")
        self.assertEqual(
            options, dict(title="hello_world", media="RP80x297", scaling="fit")
        )
        self.assertEqual(self._media_box(data_b64), (0.0, 0.0, 226.77, 841.89))

    def test_convert_binie_document_size(self):
        data = base64.b64decode(colony_print.controllers.node.HELLO_WORLD_B64)
        data = data[:256] + struct.pack("<II", 800, 1000) + data[264:]
        data_b64, options = self.node._convert_binie(
            base64.b64encode(data).decode("utf-8"),
            printer="Receipt",
            options=dict(media="A4"),
        )
        self.assertEqual(options, dict(media="Custom.80x100mm", scaling="none"))
        media_box = self._media_box(data_b64)
        self.assertAlmostEqual(media_box[2], 226.77, places=2)
        self.assertAlmostEqual(media_box[3], 283.46, places=2)

    def test_convert_binie_no_device(self):
        MockNPColony.devices = []
        data_b64, options = self.node._convert_binie(
            colony_print.controllers.node.HELLO_WORLD_B64,
            printer="missing",
            options=dict(media="Custom.80x200mm"),
        )
        self.assertEqual(options, dict(scaling="none"))
        media_box = self._media_box(data_b64)
        self.assertAlmostEqual(media_box[2], 595.28, places=2)
        self.assertAlmostEqual(media_box[3], 841.89, places=2)

    def test_convert_binie_legacy_device(self):
        MockNPColony.devices = [
            dict(
                name="legacy", is_default=True, media="A5", width=419.53, length=595.28
            )
        ]
        data_b64, options = self.node._convert_binie(
            colony_print.controllers.node.HELLO_WORLD_B64
        )
        self.assertEqual(options, dict(media="A5", scaling="none"))
        self.assertEqual(self._media_box(data_b64), (0.0, 0.0, 419.53, 595.28))

    def test_device(self):
        self.assertEqual(self.node._device("Receipt"), RECEIPT_DEVICE)
        self.assertEqual(self.node._device("receipt"), RECEIPT_DEVICE)
        self.assertEqual(self.node._device("office"), OFFICE_DEVICE)
        self.assertEqual(self.node._device("default"), OFFICE_DEVICE)
        self.assertEqual(self.node._device(""), OFFICE_DEVICE)
        self.assertEqual(self.node._device(None), OFFICE_DEVICE)
        self.assertEqual(self.node._device("missing"), dict())

        MockNPColony.devices = [RECEIPT_DEVICE, dict(OFFICE_DEVICE, is_default=False)]
        self.assertEqual(self.node._device("default"), dict())

        MockNPColony.devices = [RECEIPT_DEVICE]
        self.assertEqual(self.node._device("default"), RECEIPT_DEVICE)

        MockNPColony.devices = []
        self.assertEqual(self.node._device("default"), dict())

    def test_handle_gravo_forwards_check_path(self):
        self.node._handle_gravo(self._gravo_payload(check_path=True, dry_run=True))
        self.assertEqual(len(MockGravostyleAPI.calls), 1)
        self.assertEqual(MockGravostyleAPI.calls[0]["check_path"], True)

    def test_handle_gravo_check_path_defaults_to_false(self):
        self.node._handle_gravo(self._gravo_payload(dry_run=True))
        self.assertEqual(len(MockGravostyleAPI.calls), 1)
        self.assertEqual(MockGravostyleAPI.calls[0]["check_path"], False)

    def test_stage_extra_fonts_writes_payloads(self):
        payload_a = b"\x00\x01\x00\x00font-a-payload"
        payload_b = b"\x00\x01\x00\x00font-b-payload"
        extra_fonts = dict(
            font_a=base64.b64encode(payload_a),
            font_b=base64.b64encode(payload_b),
        )
        paths = self.node._stage_extra_fonts(extra_fonts, self.target_dir)
        self.assertEqual(
            sorted(paths.keys()),
            ["font_a", "font_b"],
        )
        self.assertEqual(paths["font_a"], os.path.join(self.target_dir, "font_a.f3s"))
        self.assertEqual(paths["font_b"], os.path.join(self.target_dir, "font_b.f3s"))
        with open(paths["font_a"], "rb") as file:
            self.assertEqual(file.read(), payload_a)
        with open(paths["font_b"], "rb") as file:
            self.assertEqual(file.read(), payload_b)

    def test_stage_extra_fonts_empty_mapping(self):
        paths = self.node._stage_extra_fonts({}, self.target_dir)
        self.assertEqual(paths, {})
        self.assertEqual(os.listdir(self.target_dir), [])

    def test_stage_extra_fonts_overrides_existing(self):
        existing_path = os.path.join(self.target_dir, "font_a.f3s")
        with open(existing_path, "wb") as file:
            file.write(b"stale")
        payload = b"\x00\x01\x00\x00fresh-payload"
        paths = self.node._stage_extra_fonts(
            dict(font_a=base64.b64encode(payload)), self.target_dir
        )
        with open(paths["font_a"], "rb") as file:
            self.assertEqual(file.read(), payload)

    def test_decode_payload_json(self):
        data = json.dumps(dict(text="Hello World", font="HELVETICA 1L"))
        data_b64 = base64.b64encode(data.encode("utf-8"))
        payload = self.node._decode_payload(data_b64)
        self.assertEqual(payload, dict(text="Hello World", font="HELVETICA 1L"))

    def test_decode_payload_unicode(self):
        original = dict(text=appier.legacy.u("é✨"))
        data_b64 = base64.b64encode(json.dumps(original).encode("utf-8"))
        payload = self.node._decode_payload(data_b64)
        self.assertEqual(payload, original)

    def test_decode_payload_multifont(self):
        data = json.dumps(dict(text=[["HELVETICA 1L", "A"], ["TIMES 1L", "B"]]))
        data_b64 = base64.b64encode(data.encode("utf-8"))
        payload = self.node._decode_payload(data_b64)
        self.assertEqual(payload, dict(text=[["HELVETICA 1L", "A"], ["TIMES 1L", "B"]]))

    def test_decode_payload_invalid(self):
        data_b64 = base64.b64encode(b"not a json payload")
        self.assertRaises(ValueError, lambda: self.node._decode_payload(data_b64))

    def test_ensure_format(self):
        self.node._ensure_format(None)
        self.node._ensure_format("pdf")
        self.node._ensure_format("binie")
        self.assertRaises(
            appier.OperationalError, lambda: self.node._ensure_format("zpl")
        )

        MockNPColony.format = "binie"
        self.node._ensure_format("binie")
        self.assertRaises(
            appier.OperationalError, lambda: self.node._ensure_format("pdf")
        )

        sys.modules["npcolony"] = MockNPColonyLegacy
        self.node._ensure_format("pdf")
