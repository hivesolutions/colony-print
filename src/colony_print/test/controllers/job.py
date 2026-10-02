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
        self.app = colony_print.ColonyPrintApp(
            level=logging.ERROR, session_c=appier.MemorySession
        )
        self._notify = appier.notify
        appier.notify = lambda *args, **kwargs: None
        session = self.app.session_c.new()
        session["username"] = "admin"
        session["tokens"] = ["admin"]
        self.headers = [("X-Session-Id", session.sid)]

    def tearDown(self):
        appier.notify = self._notify
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

    def test_clone_fonts(self):
        fonts = [dict(name="Colonia", data_b64="QUJD")]
        self.app.jobs_info["name"] = dict(
            id="name",
            name="document",
            node_id="node",
            data_length=4,
            format="binie",
            fonts=[dict(name="Colonia", data_length=4)],
            status="finished",
            result=dict(result="success"),
        )
        self.app.jobs_data["name"] = "QUJD"
        self.app.jobs_fonts["name"] = fonts
        response = self.app.post("/jobs/name/clone", headers=self.headers)
        self.assertEqual(response.code, 200)
        clone_info = json.loads(response.data.decode("utf-8"))
        self.assertEqual(clone_info["status"], "queued")
        self.assertEqual(clone_info["fonts"], [dict(name="Colonia", data_length=4)])
        self.assertEqual("result" in clone_info, False)
        self.assertEqual(self.app.jobs_fonts[clone_info["id"]], fonts)
        job = self.app.jobs["node"][0]
        self.assertEqual(job["id"], clone_info["id"])
        self.assertEqual(job["data_b64"], "QUJD")
        self.assertEqual(job["fonts"], fonts)

        # a job whose fonts were declared by its document (only their
        # information is kept) is cloned without sending them to the node
        self.app.jobs_info["xmpl"] = dict(
            id="xmpl",
            name="xmpl",
            node_id="node",
            format="xmpl",
            fonts=[dict(name="Colonia", data_length=4)],
        )
        self.app.jobs_data["xmpl"] = "QUJD"
        response = self.app.post("/jobs/xmpl/clone", headers=self.headers)
        self.assertEqual(response.code, 200)
        clone_info = json.loads(response.data.decode("utf-8"))
        self.assertEqual(clone_info["fonts"], [dict(name="Colonia", data_length=4)])
        self.assertEqual("fonts" in self.app.jobs["node"][1], False)
        self.assertEqual(clone_info["id"] in self.app.jobs_fonts, False)

        # a job without fonts is cloned without any font
        self.app.jobs_info["other"] = dict(id="other", name="other", node_id="node")
        self.app.jobs_data["other"] = "QUJD"
        response = self.app.post("/jobs/other/clone", headers=self.headers)
        self.assertEqual(response.code, 200)
        clone_info = json.loads(response.data.decode("utf-8"))
        self.assertEqual("fonts" in clone_info, False)
        self.assertEqual(clone_info["id"] in self.app.jobs_fonts, False)
        self.assertEqual("fonts" in self.app.jobs["node"][2], False)

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

    def test_jobs_light_excludes_output_data(self):
        controller = colony_print.controllers.JobController(self.app)
        self.app.jobs_info["name"] = dict(
            id="name",
            name="document",
            result=dict(result="success", output_data="QkxPQg=="),
        )
        jobs = controller.jobs_light
        self.assertEqual("output_data" in jobs["name"]["result"], False)
        self.assertEqual("output_data" in self.app.jobs_info["name"]["result"], True)

    def test_slim_job_info_strips_output_data(self):
        controller = colony_print.controllers.JobController(self.app)
        job_info = dict(
            id="name",
            name="document",
            result=dict(
                result="success",
                output_data="QkxPQg==",
                output_mime_type="application/pdf",
            ),
        )
        slim = controller.slim_job_info(job_info)
        self.assertEqual("output_data" in slim["result"], False)
        self.assertEqual(slim["result"]["output_mime_type"], "application/pdf")
        self.assertEqual("output_data" in job_info["result"], True)

    def test_slim_job_info_strips_traceback(self):
        controller = colony_print.controllers.JobController(self.app)
        job_info = dict(
            id="name",
            name="document",
            result=dict(result="error", error="boom", traceback="Traceback ..."),
        )
        slim = controller.slim_job_info(job_info)
        self.assertEqual("traceback" in slim["result"], False)
        self.assertEqual(slim["result"]["error"], "boom")
        self.assertEqual("traceback" in job_info["result"], True)

    def test_slim_job_info_without_result(self):
        controller = colony_print.controllers.JobController(self.app)
        job_info = dict(id="name", name="document", status="queued")
        slim = controller.slim_job_info(job_info)
        self.assertEqual(slim, dict(id="name", name="document", status="queued"))

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

    def test_enrich_job_info_fonts(self):
        # the (JSON) payload of the jobs of the fonts type is not decoded,
        # as it holds the (heavy) data of the fonts, only their (light)
        # information is kept by the job
        controller = colony_print.controllers.JobController(self.app)
        data = json.dumps(dict(fonts=[dict(name="Colonia", data_b64="QUJD")]))
        data_b64 = base64.b64encode(data.encode("utf-8"))
        fonts = [dict(name="Colonia", data_length=4)]
        self.app.jobs_info["name"] = dict(
            id="name", name="fonts", type="fonts", fonts=fonts
        )
        self.app.jobs_data["name"] = data_b64
        job_info = controller.enrich_job_info(self.app.jobs_info["name"])
        self.assertEqual("request_payload" in job_info, False)
        self.assertEqual(job_info["fonts"], fonts)
        self.assertEqual(self.app.jobs_data["name"], data_b64)

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
