#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import unittest

import appier

import colony_print


class JobControllerTest(unittest.TestCase):
    def setUp(self):
        self.app = colony_print.ColonyPrintApp(level=logging.ERROR)

    def tearDown(self):
        self.app.unload()
        adapter = appier.get_adapter()
        adapter.drop_db()

    def test_list(self):
        response = self.app.get("/jobs")
        self.assertEqual(response.code, 403)

    def test_list_o(self):
        response = self.app.options("/jobs")
        self.assertEqual(response.code, 200)
        self.assertEqual(
            response.headers["Access-Control-Allow-Origin"].startswith("*"), True
        )
        self.assertEqual(
            response.headers["Access-Control-Allow-Headers"].startswith("*"), True
        )

    def test_show(self):
        response = self.app.get("/jobs/name")
        self.assertEqual(response.code, 403)

    def test_show_o(self):
        response = self.app.options("/jobs/name")
        self.assertEqual(response.code, 200)
        self.assertEqual(
            response.headers["Access-Control-Allow-Origin"].startswith("*"), True
        )
        self.assertEqual(
            response.headers["Access-Control-Allow-Headers"].startswith("*"), True
        )

    def test_cancel(self):
        response = self.app.post("/jobs/name/cancel")
        self.assertEqual(response.code, 403)

    def test_cancel_o(self):
        response = self.app.options("/jobs/name/cancel")
        self.assertEqual(response.code, 200)
        self.assertEqual(
            response.headers["Access-Control-Allow-Origin"].startswith("*"), True
        )
        self.assertEqual(
            response.headers["Access-Control-Allow-Headers"].startswith("*"), True
        )

    def test_files(self):
        response = self.app.get("/jobs/name/files")
        self.assertEqual(response.code, 403)

    def test_files_o(self):
        response = self.app.options("/jobs/name/files")
        self.assertEqual(response.code, 200)
        self.assertEqual(
            response.headers["Access-Control-Allow-Origin"].startswith("*"), True
        )
        self.assertEqual(
            response.headers["Access-Control-Allow-Headers"].startswith("*"), True
        )

    def test_file(self):
        response = self.app.get("/jobs/name/files/file.txt")
        self.assertEqual(response.code, 403)

    def test_file_o(self):
        response = self.app.options("/jobs/name/files/file.txt")
        self.assertEqual(response.code, 200)
        self.assertEqual(
            response.headers["Access-Control-Allow-Origin"].startswith("*"), True
        )
        self.assertEqual(
            response.headers["Access-Control-Allow-Headers"].startswith("*"), True
        )
