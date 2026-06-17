#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import json
import base64
import shutil
import tempfile
import unittest

import appier

import colony_print.node


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


class ColonyPrintNodeTest(unittest.TestCase):
    def setUp(self):
        self.node = colony_print.node.ColonyPrintNode()
        self.target_dir = tempfile.mkdtemp(prefix="colony-print-fonts-test-")
        MockGravostyleAPI.calls = []
        self._gravo_pilot = sys.modules.get("gravo_pilot")
        sys.modules["gravo_pilot"] = MockGravoPilot

    def tearDown(self):
        shutil.rmtree(self.target_dir, ignore_errors=True)
        if self._gravo_pilot == None:
            sys.modules.pop("gravo_pilot", None)
        else:
            sys.modules["gravo_pilot"] = self._gravo_pilot

    def _gravo_payload(self, **kwargs):
        data = dict(text="Hello World")
        data.update(kwargs)
        return base64.b64encode(json.dumps(data).encode("utf-8"))

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
