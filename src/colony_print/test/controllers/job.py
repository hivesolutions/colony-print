#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import base64
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

    def test_clone(self):
        response = self.app.post("/jobs/name/clone")
        self.assertEqual(response.code, 403)

    def test_clone_o(self):
        response = self.app.options("/jobs/name/clone")
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

    def test_payload(self):
        response = self.app.get("/jobs/name/payload")
        self.assertEqual(response.code, 403)

    def test_payload_o(self):
        response = self.app.options("/jobs/name/payload")
        self.assertEqual(response.code, 200)
        self.assertEqual(
            response.headers["Access-Control-Allow-Origin"].startswith("*"), True
        )
        self.assertEqual(
            response.headers["Access-Control-Allow-Headers"].startswith("*"), True
        )

    def test_enrich_job_info_includes_payload(self):
        controller = colony_print.controllers.JobController(self.app)
        data = json.dumps(dict(text="Hello World", font="HELVETICA 1L"))
        data_b64 = base64.b64encode(data.encode("utf-8"))
        self.app.jobs_info["name"] = dict(id="name", name="document")
        self.app.jobs_data["name"] = data_b64
        job_info = controller.enrich_job_info(self.app.jobs_info["name"])
        self.assertEqual(job_info["id"], "name")
        self.assertEqual(
            job_info["request_payload"],
            dict(text="Hello World", font="HELVETICA 1L"),
        )
        self.assertEqual("request_payload" in self.app.jobs_info["name"], False)

    def test_enrich_job_info_binary_data(self):
        controller = colony_print.controllers.JobController(self.app)
        self.app.jobs_info["name"] = dict(id="name", name="document")
        self.app.jobs_data["name"] = base64.b64encode(b"\x00\x01\x00\x00binary-payload")
        job_info = controller.enrich_job_info(self.app.jobs_info["name"])
        self.assertEqual("request_payload" in job_info, False)

    def test_enrich_job_info_without_data(self):
        controller = colony_print.controllers.JobController(self.app)
        job_info = controller.enrich_job_info(dict(id="name", name="document"))
        self.assertEqual("request_payload" in job_info, False)

    def test_decode_payload_json(self):
        controller = colony_print.controllers.JobController(self.app)
        data = json.dumps(dict(text="Hello World", font="HELVETICA 1L"))
        data_b64 = base64.b64encode(data.encode("utf-8"))
        payload = controller._decode_payload(data_b64)
        self.assertEqual(payload, dict(text="Hello World", font="HELVETICA 1L"))

    def test_decode_payload_binary(self):
        controller = colony_print.controllers.JobController(self.app)
        data_b64 = base64.b64encode(b"\x00\x01\x00\x00binary-payload")
        payload = controller._decode_payload(data_b64)
        self.assertEqual(payload, None)

    def test_decode_payload_invalid(self):
        controller = colony_print.controllers.JobController(self.app)
        payload = controller._decode_payload("!!!not-base64!!!")
        self.assertEqual(payload, None)
