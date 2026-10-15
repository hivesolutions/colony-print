#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import logging
import unittest

import appier

import colony_print


class PrinterControllerTest(unittest.TestCase):
    def setUp(self):
        self.app = colony_print.ColonyPrintApp(
            level=logging.ERROR, session_c=appier.MemorySession
        )
        session = self.app.session_c.new()
        session["username"] = "admin"
        session["tokens"] = ["admin"]
        self.headers = [("X-Session-Id", session.sid)]

    def tearDown(self):
        self.app.unload()
        adapter = appier.get_adapter()
        adapter.drop_db()

    def test_nodes(self):
        response = self.app.get("/printers/nodes")
        self.assertEqual(response.code, 403)

        response = self.app.get("/printers/nodes", headers=self.headers)
        self.assertEqual(response.code, 200)
        self.assertEqual(json.loads(response.data.decode("utf-8")), [])

        # the printers of the nodes are the ones reported by each node, an
        # engraver being listed for the nodes with the gravo engine
        self.app.nodes["shop"] = dict(
            name="Shop",
            printer="default",
            engines=["npcolony"],
            engine_info=dict(colony=dict(devices=[dict(name="Receipt")])),
            last_ping=100.0,
        )
        self.app.nodes["engraver"] = dict(name="Engraver", engines=["gravo"])
        response = self.app.get("/printers/nodes", headers=self.headers)
        self.assertEqual(response.code, 200)
        self.assertEqual(
            json.loads(response.data.decode("utf-8")),
            [
                dict(
                    name="Gravo engraver",
                    engine="gravo",
                    node_id="engraver",
                    node_name="Engraver",
                    node_printer=None,
                    last_ping=None,
                ),
                dict(
                    name="Receipt",
                    engine="npcolony",
                    node_id="shop",
                    node_name="Shop",
                    node_printer="default",
                    last_ping=100.0,
                ),
            ],
        )
