#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import unittest

import appier

import colony_print

class NodeControllerTest(unittest.TestCase):

    def setUp(self):
        self.app = colony_print.ColonyPrintApp(level = logging.ERROR)

    def tearDown(self):
        self.app.unload()
        adapter = appier.get_adapter()
        adapter.drop_db()

    def test_print_default(self):
        response = self.app.get("/nodes/name/print")
        self.assertEqual(response.code, 403)

    def test_print_default_o(self):
        response = self.app.options("/nodes/name/print")
        self.assertEqual(response.code, 200)
        self.assertEqual(response.headers["Access-Control-Allow-Origin"].startswith("*"), True)
        self.assertEqual(response.headers["Access-Control-Allow-Headers"].startswith("*"), True)
