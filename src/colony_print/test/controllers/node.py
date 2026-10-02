#!/usr/bin/python
# -*- coding: utf-8 -*-

import json
import base64
import logging
import unittest

import appier

import colony_print

XMPL = '<?xml version="1.0" encoding="UTF-8"?>\
    <printing_document name="hello_world" font="Colonia" font_size="9">\
        %s\
        <paragraph text_align="center">\
            <line><text>Hello World</text></line>\
        </paragraph>\
    </printing_document>'
""" The template of the hello world XMPL document, with its font
elements (declarations) """


class NodeControllerTest(unittest.TestCase):
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

    def _node(
        self, id="node", capabilities=["npcolony", "binie", "xmpl", "dynamic-fonts"]
    ):
        self.app.nodes[id] = dict(name=id, capabilities=capabilities)

    def _print(self, url="/nodes/node/print", **kwargs):
        params = dict(data_b64="SGVsbG8gV29ybGQ=")
        params.update(kwargs)
        for name in ("options", "fonts"):
            if name in params and not appier.legacy.is_string(params[name]):
                params[name] = json.dumps(params[name])
        params = dict(
            (key, value) for key, value in params.items() if not value == None
        )
        response = self.app.post(
            url, query=appier.legacy.urlencode(params), headers=self.headers
        )
        return response.code, json.loads(response.data.decode("utf-8"))

    def _xmpl(self, fonts=[]):
        elements = "".join(
            "<font %s/>" % " ".join('%s="%s"' % item for item in sorted(font.items()))
            for font in fonts
        )
        return XMPL % elements

    def test_show(self):
        response = self.app.get("/nodes/name")
        self.assertEqual(response.code, 403)

    def test_print_default(self):
        response = self.app.get("/nodes/name/print")
        self.assertEqual(response.code, 403)

    def test_print_default_fonts(self):
        self._node()
        fonts = [
            dict(name="Colonia", data_b64="QUJDRA=="),
            dict(name="Binaria", style="bold", url="https://fonts.hive.pt/b.ttf"),
            dict(name="Calibri", md5="a" * 32),
        ]
        code, job_info = self._print(format="binie", fonts=fonts)
        self.assertEqual(code, 200)
        self.assertEqual(job_info["status"], "queued")
        self.assertEqual(
            job_info["fonts"],
            [
                dict(name="Colonia", data_length=8),
                dict(name="Binaria", style="bold", url="https://fonts.hive.pt/b.ttf"),
                dict(name="Calibri", md5="a" * 32),
            ],
        )
        self.assertEqual(self.app.jobs_info[job_info["id"]]["fonts"], job_info["fonts"])
        self.assertEqual(self.app.jobs_fonts[job_info["id"]], fonts)
        job = self.app.jobs["node"][0]
        self.assertEqual(job["fonts"], fonts)
        self.assertEqual(job["format"], "binie")

        # a job without fonts doesn't keep any font (information)
        code, job_info = self._print(format="binie")
        self.assertEqual(code, 200)
        self.assertEqual("fonts" in job_info, False)
        self.assertEqual(job_info["id"] in self.app.jobs_fonts, False)
        self.assertEqual("fonts" in self.app.jobs["node"][1], False)

    def test_print_default_fonts_invalid(self):
        self._node()
        font = dict(name="Colonia", data_b64="QUJD")
        invalid = [
            dict(format="binie", fonts="not json"),
            dict(format="binie", fonts=dict(name="Colonia", data_b64="QUJD")),
            dict(format="binie", fonts=["Colonia"]),
            dict(format="binie", fonts=[dict(name="Colonia")]),
            dict(format="binie", fonts=[font, dict(name="Colonia", md5="../index")]),
            dict(format="pdf", fonts=[font]),
            dict(fonts=[font]),
        ]
        for params in invalid:
            code, result = self._print(**params)
            self.assertEqual(code, 400)
            self.assertEqual(result["result"], "error")
        self.assertEqual(self.app.jobs.get("node", []), [])

    def test_print_default_fonts_capability(self):
        font = dict(name="Colonia", data_b64="QUJD")
        code, result = self._print(
            url="/nodes/unknown/print", format="binie", fonts=[font]
        )
        self.assertEqual(code, 409)
        self.assertEqual(
            result["message"], "Node 'unknown' doesn't support 'dynamic-fonts'"
        )

        self._node(capabilities=["npcolony", "binie", "xmpl"])
        code, result = self._print(format="binie", fonts=[font])
        self.assertEqual(code, 409)

        # an older node that doesn't advertise its capabilities
        self.app.nodes["node"] = dict(name="node")
        code, result = self._print(format="binie", fonts=[font])
        self.assertEqual(code, 409)
        self.assertEqual(self.app.jobs.get("node", []), [])

    def test_print_default_xmpl(self):
        self._node(capabilities=["npcolony", "binie", "xmpl"])
        code, job_info = self._print(data_b64=None, data=self._xmpl(), format="xmpl")
        self.assertEqual(code, 200)
        self.assertEqual(job_info["format"], "xmpl")
        self.assertEqual("fonts" in job_info, False)
        job = self.app.jobs["node"][0]
        self.assertEqual(
            base64.b64decode(job["data_b64"]), self._xmpl().encode("utf-8")
        )

        # a document declaring fonts (with the ones of the request) requires
        # the node to support the fonts, the information of both is kept
        declared = dict(name="Colonia", url="https://fonts.hive.pt/colonia.ttf")
        font = dict(name="Binaria", data_b64="QUJD")
        data = self._xmpl(fonts=[declared])
        code, result = self._print(data_b64=None, data=data, format="xmpl")
        self.assertEqual(code, 409)

        self._node()
        code, job_info = self._print(
            data_b64=None, data=data, format="xmpl", fonts=[font]
        )
        self.assertEqual(code, 200)
        self.assertEqual(
            job_info["fonts"], [declared, dict(name="Binaria", data_length=4)]
        )
        self.assertEqual(self.app.jobs["node"][1]["fonts"], [font])

        # a document declaring its fonts without the fonts field, whose job
        # keeps their information but sends no fonts to the node (it reads
        # them from the document)
        declared = dict(name="Colonia", data_b64="QUJD")
        code, job_info = self._print(
            data_b64=None, data=self._xmpl(fonts=[declared]), format="xmpl"
        )
        self.assertEqual(code, 200)
        self.assertEqual(job_info["fonts"], [dict(name="Colonia", data_length=4)])
        self.assertEqual("fonts" in self.app.jobs["node"][2], False)
        self.assertEqual(job_info["id"] in self.app.jobs_fonts, False)

    def test_print_default_xmpl_invalid(self):
        self._node(capabilities=["npcolony", "binie", "dynamic-fonts"])
        code, result = self._print(data_b64=None, data=self._xmpl(), format="xmpl")
        self.assertEqual(code, 409)
        self.assertEqual(result["message"], "Node 'node' doesn't support 'xmpl'")

        self._node()
        code, result = self._print(
            data_b64=None, data="<printing_document", format="xmpl"
        )
        self.assertEqual(code, 400)
        self.assertEqual(result["message"], "Document is not a valid XMPL document")

        # documents that are well formed but that can't be converted (no
        # name for the printing document or another root element)
        for data in ("<printing_document/>", '<html name="hello_world"/>'):
            code, result = self._print(data_b64=None, data=data, format="xmpl")
            self.assertEqual(code, 400)

        # images read from the file system (of the node) are refused, only
        # inline images (source) may be printed
        data = '<printing_document name="logo"><image path="C:\\logo.bmp"/></printing_document>'
        code, result = self._print(data_b64=None, data=data, format="xmpl")
        self.assertEqual(code, 400)
        self.assertEqual(
            result["message"], "Images of the document must be inline (source)"
        )

        data = self._xmpl(fonts=[dict(name="Colonia", url="ftp://fonts.hive.pt/c.ttf")])
        code, result = self._print(data_b64=None, data=data, format="xmpl")
        self.assertEqual(code, 400)
        self.assertEqual(self.app.jobs.get("node", []), [])

    def test_print_default_o(self):
        response = self.app.options("/nodes/name/print")
        self.assertEqual(response.code, 200)
        self.assertEqual(
            response.headers["Access-Control-Allow-Origin"].startswith("*"), True
        )
        self.assertEqual(
            response.headers["Access-Control-Allow-Headers"].startswith("*"), True
        )

    def test_print_printer_fonts(self):
        self._node()
        fonts = [dict(name="Colonia", data_b64="QUJD")]
        code, job_info = self._print(
            url="/nodes/node/printers/receipt/print", format="binie", fonts=fonts
        )
        self.assertEqual(code, 200)
        self.assertEqual(job_info["printer"], "receipt")
        self.assertEqual(job_info["fonts"], [dict(name="Colonia", data_length=4)])
        self.assertEqual(self.app.jobs["node"][0]["fonts"], fonts)
        self.assertEqual(self.app.jobs_fonts[job_info["id"]], fonts)

        code, job_info = self._print(
            url="/nodes/node/printers/receipt/print",
            data_b64=None,
            data=self._xmpl(fonts=[dict(name="Colonia", data_b64="QUJD")]),
            format="xmpl",
        )
        self.assertEqual(code, 200)
        self.assertEqual(job_info["fonts"], [dict(name="Colonia", data_length=4)])
        self.assertEqual("fonts" in self.app.jobs["node"][1], False)

        code, result = self._print(
            url="/nodes/node/printers/receipt/print", format="pdf", fonts=fonts
        )
        self.assertEqual(code, 400)

    def test_fonts(self):
        response = self.app.get("/nodes/node/fonts")
        self.assertEqual(response.code, 403)

        response = self.app.get("/nodes/node/fonts", headers=self.headers)
        self.assertEqual(response.code, 409)

        fonts = [dict(name="Colonia", style="regular", md5="a" * 32, active=True)]
        self._node()
        self.app.nodes["node"]["fonts"] = fonts
        response = self.app.get("/nodes/node/fonts", headers=self.headers)
        self.assertEqual(response.code, 200)
        self.assertEqual(json.loads(response.data.decode("utf-8")), fonts)

        del self.app.nodes["node"]["fonts"]
        response = self.app.get("/nodes/node/fonts", headers=self.headers)
        self.assertEqual(response.code, 200)
        self.assertEqual(json.loads(response.data.decode("utf-8")), [])

    def test_install_fonts(self):
        response = self.app.post("/nodes/node/fonts")
        self.assertEqual(response.code, 403)

        fonts = [
            dict(name="Colonia", data_b64="QUJD"),
            dict(name="Binaria", url="https://fonts.hive.pt/binaria.ttf"),
        ]
        code, result = self._print(url="/nodes/node/fonts", data_b64=None, fonts=fonts)
        self.assertEqual(code, 409)

        self._node()
        code, job_info = self._print(
            url="/nodes/node/fonts", data_b64=None, fonts=fonts
        )
        self.assertEqual(code, 200)
        self.assertEqual(job_info["name"], "fonts")
        self.assertEqual(job_info["type"], "fonts")
        self.assertEqual(job_info["status"], "queued")
        self.assertEqual("fonts" in job_info, False)
        self.assertEqual("format" in job_info, False)
        job = self.app.jobs["node"][0]
        self.assertEqual(
            json.loads(base64.b64decode(job["data_b64"]).decode("utf-8")),
            dict(fonts=fonts),
        )
        self.assertEqual("fonts" in job, False)

        # the fonts may be installed with another name of the job, the
        # data, the format and the fonts of the request being ignored
        code, job_info = self._print(
            url="/nodes/node/fonts",
            name="label fonts",
            format="binie",
            fonts=fonts[:1],
        )
        self.assertEqual(code, 200)
        self.assertEqual(job_info["name"], "label fonts")
        job = self.app.jobs["node"][1]
        self.assertEqual(
            json.loads(base64.b64decode(job["data_b64"]).decode("utf-8")),
            dict(fonts=fonts[:1]),
        )

    def test_install_fonts_invalid(self):
        self._node()
        invalid = [
            dict(),
            dict(fonts=[]),
            dict(fonts=dict(name="Colonia", data_b64="QUJD")),
            dict(fonts=[dict(name="Colonia", md5="a" * 32)]),
            dict(fonts=[dict(name="Colonia")]),
            dict(fonts="not json"),
        ]
        for params in invalid:
            code, result = self._print(url="/nodes/node/fonts", data_b64=None, **params)
            self.assertEqual(code, 400)
        self.assertEqual(self.app.jobs.get("node", []), [])

    def test_fonts_o(self):
        response = self.app.options("/nodes/node/fonts")
        self.assertEqual(response.code, 200)
        self.assertEqual(
            response.headers["Access-Control-Allow-Origin"].startswith("*"), True
        )
        self.assertEqual(
            response.headers["Access-Control-Allow-Headers"].startswith("*"), True
        )

    def test_valid_options(self):
        valid_options = colony_print.controllers.node.VALID_OPTIONS
        self.assertEqual("media" in valid_options, True)
        self.assertEqual("scaling" in valid_options, True)
        self.assertEqual("title" in valid_options, False)
        self.assertEqual("output_path" in valid_options, False)

    def test_enrich_node_includes_stats(self):
        controller = colony_print.controllers.NodeController(self.app)
        self.app.nodes["name"] = dict(name="Node", libraries=dict(appier="1.0.0"))
        self.app.jobs_info["first"] = dict(
            id="first",
            name="document",
            node_id="name",
            status="finished",
            finish_time=100.0,
            result=dict(result="success"),
        )
        self.app.jobs_info["second"] = dict(
            id="second", name="document", node_id="other", status="queued"
        )
        node = controller.enrich_node("name", self.app.nodes["name"])
        self.assertEqual(node["name"], "Node")
        self.assertEqual(node["libraries"], dict(appier="1.0.0"))
        self.assertEqual(
            node["stats"],
            dict(
                total=1,
                finished=1,
                error=0,
                in_flight=0,
                cancelled=0,
                last=dict(
                    id="first", name="document", finish_time=100.0, result="success"
                ),
            ),
        )
        self.assertEqual("stats" in self.app.nodes["name"], False)

    def test_enrich_node_without_jobs(self):
        controller = colony_print.controllers.NodeController(self.app)
        node = controller.enrich_node("name", dict(name="Node"))
        self.assertEqual(
            node,
            dict(
                name="Node",
                stats=dict(total=0, finished=0, error=0, in_flight=0, cancelled=0),
            ),
        )

    def test_verify_fonts(self):
        controller = colony_print.controllers.NodeController(self.app)
        self._node()
        data_b64 = base64.b64encode(
            self._xmpl(fonts=[dict(name="Colonia", md5="a" * 32)]).encode("utf-8")
        )
        self.assertEqual(controller._verify_fonts("node", data_b64), [])
        self.assertEqual(controller._verify_fonts("node", data_b64, format="pdf"), [])
        self.assertEqual(
            controller._verify_fonts("node", data_b64, format="xmpl"),
            [dict(name="Colonia", md5="a" * 32)],
        )
        self.assertEqual(
            controller._verify_fonts(
                "node",
                data_b64,
                format="xmpl",
                fonts=[dict(name="Binaria", style="italic", data_b64="QUJD", extra=1)],
            ),
            [
                dict(name="Colonia", md5="a" * 32),
                dict(name="Binaria", style="italic", data_length=4),
            ],
        )
        self.assertRaises(
            appier.OperationalError,
            lambda: controller._verify_fonts(
                "node", data_b64, format="binie", fonts=dict(name="Colonia")
            ),
        )
        self.assertRaises(
            appier.OperationalError,
            lambda: controller._verify_fonts(
                "other",
                data_b64,
                format="binie",
                fonts=[dict(name="Colonia", md5="a" * 32)],
            ),
        )

    def test_verify_xmpl(self):
        controller = colony_print.controllers.NodeController(self.app)
        controller._verify_xmpl(self._xmpl().encode("utf-8"))
        controller._verify_xmpl(
            self._xmpl(fonts=[dict(name="Colonia", md5="a" * 32)]).encode("utf-8")
        )
        for data in (
            b"<printing_document/>",
            b'<html name="hello_world"/>',
            b"<printing_document",
            b"not xml",
        ):
            self.assertRaises(Exception, lambda: controller._verify_xmpl(data))
        self.assertRaises(
            appier.OperationalError,
            lambda: controller._verify_xmpl(b'<html name="hello_world"/>'),
        )
        self.assertRaises(
            appier.OperationalError,
            lambda: controller._verify_xmpl(
                b'<printing_document name="logo"><image path="logo.bmp"/></printing_document>'
            ),
        )

    def test_ensure_capability(self):
        controller = colony_print.controllers.NodeController(self.app)
        self._node()
        controller._ensure_capability("node", "xmpl")
        controller._ensure_capability("node", "dynamic-fonts")
        self.assertRaises(
            appier.OperationalError,
            lambda: controller._ensure_capability("node", "email"),
        )
        self.assertRaises(
            appier.OperationalError,
            lambda: controller._ensure_capability("unknown", "xmpl"),
        )

        self.app.nodes["node"] = dict(name="node")
        self.assertRaises(
            appier.OperationalError,
            lambda: controller._ensure_capability("node", "xmpl"),
        )
