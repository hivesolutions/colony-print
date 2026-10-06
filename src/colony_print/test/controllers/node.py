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

    def _register(self, id="node", **kwargs):
        # registers the node with the provided information, as the node
        # does on every iteration of its loop
        response = self.app.post(
            "/nodes/%s" % id,
            data=json.dumps(kwargs).encode("utf-8"),
            headers=self.headers + [("Content-Type", "application/json")],
        )
        return response.code

    def _deliver(self, id="node"):
        # retrieves the queued jobs of the node, as the node does, which
        # makes them the ones that are in flight (printing)
        controller = colony_print.controllers.NodeController(self.app)
        return json.loads(list(controller.wait_jobs(id))[0])

    def _xmpl(self, fonts=[]):
        elements = "".join(
            "<font %s/>" % " ".join('%s="%s"' % item for item in sorted(font.items()))
            for font in fonts
        )
        return XMPL % elements

    def test_create(self):
        response = self.app.post("/nodes/node")
        self.assertEqual(response.code, 403)

        code = self._register(name="Node", version="0.23.0")
        self.assertEqual(code, 200)
        self.assertEqual(self.app.nodes["node"]["name"], "Node")
        self.assertEqual(type(self.app.nodes["node"]["last_ping"]), float)

        # the job that restarts the node is not finished by a result of the
        # node, but by the server once the node registers itself with a newer
        # start time, with the versions of the node before and after it
        node = dict(
            name="Node",
            capabilities=["text", "restart"],
            version="0.23.0",
            libraries=dict(appier="1.0.0", npcolony="1.7.0"),
            start_time=100.0,
        )
        self._register(**node)
        code, job_info = self._print(url="/nodes/node/restart", data_b64=None)
        self.assertEqual(code, 200)
        job_info = self.app.jobs_info[job_info["id"]]

        # the node that restarts by itself before receiving the job (still
        # queued) receives it afterwards, the job is not finished by it
        self._register(**dict(node, start_time=150.0))
        self.assertEqual(job_info["status"], "queued")

        jobs = self._deliver()
        self.assertEqual([job["id"] for job in jobs], [job_info["id"]])
        self.assertEqual("data_b64" in jobs[0], False)
        self.assertEqual(job_info["status"], "printing")

        # the node that registers itself with the same start time was not
        # restarted (eg: its restart failed), so the job stays in flight
        self._register(**dict(node, start_time=150.0))
        self.assertEqual(job_info["status"], "printing")
        self.assertEqual("result" in job_info, False)

        code = self._register(
            **dict(
                node,
                version="0.24.0",
                libraries=dict(appier="1.1.0", npcolony="1.7.0"),
                start_time=200.0,
            )
        )
        self.assertEqual(code, 200)
        self.assertEqual(job_info["status"], "finished")
        self.assertEqual(type(job_info["finish_time"]), float)
        self.assertEqual(
            job_info["result"],
            dict(
                result="success",
                handler="restart",
                before=dict(
                    version="0.23.0",
                    libraries=dict(appier="1.0.0", npcolony="1.7.0"),
                    start_time=150.0,
                ),
                after=dict(
                    version="0.24.0",
                    libraries=dict(appier="1.1.0", npcolony="1.7.0"),
                    start_time=200.0,
                ),
            ),
        )
        self.assertEqual(self.app.nodes["node"]["version"], "0.24.0")

        # the job is also finished when the start time of the restarted
        # node is not newer (the clock of its machine went back)
        code, job_info = self._print(url="/nodes/node/restart", data_b64=None)
        job_info = self.app.jobs_info[job_info["id"]]
        self._deliver()
        self._register(**dict(node, start_time=180.0))
        self.assertEqual(job_info["status"], "finished")
        self.assertEqual(job_info["result"]["before"]["start_time"], 200.0)
        self.assertEqual(job_info["result"]["after"]["start_time"], 180.0)

        # an older node (that doesn't report its start time) registers
        # itself as before, without any job being finished
        code = self._register(id="older", name="Older", version="0.22.0")
        self.assertEqual(code, 200)
        code = self._register(id="older", name="Older", version="0.22.0")
        self.assertEqual(code, 200)
        self.assertEqual("start_time" in self.app.nodes["older"], False)

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
        self.assertEqual(self.app.jobs_fonts[job_info["id"]], None)
        self.assertEqual("fonts" in self.app.jobs["node"][1], False)

        # the fonts may also be sent for the jobs of the (explicit) npcolony
        # type, the engine that prints the documents with them
        code, job_info = self._print(type="npcolony", format="binie", fonts=fonts)
        self.assertEqual(code, 200)
        self.assertEqual(job_info["type"], "npcolony")
        self.assertEqual(len(job_info["fonts"]), 3)
        self.assertEqual(self.app.jobs["node"][2]["fonts"], fonts)

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
            dict(type="text", format="binie", fonts=[font]),
            dict(type="gravo", format="binie", fonts=[font]),
            dict(type="fonts", format="binie", fonts=[font]),
        ]
        for params in invalid:
            code, result = self._print(**params)
            self.assertEqual(code, 400)
            self.assertEqual(result["result"], "error")
        self.assertEqual(self.app.jobs.get("node", []), [])

        # the other engines don't use the fonts, that would be silently
        # ignored, so they are refused (even for the binie format)
        code, result = self._print(type="text", format="binie", fonts=[font])
        self.assertEqual(result["message"], "Fonts require the npcolony type")

    def test_print_default_fonts_capability(self):
        # the jobs with fonts are accepted for the nodes that don't support
        # the fonts (without the capability or older nodes, that don't
        # advertise their capabilities), that print their documents with
        # their own fonts, so the fonts are not sent to them (but kept for
        # the clones of the job) and they are marked as skipped
        font = dict(name="Colonia", data_b64="QUJD")
        self._node(capabilities=["npcolony", "binie", "xmpl"])
        code, job_info = self._print(format="binie", fonts=[font])
        self.assertEqual(code, 200)
        self.assertEqual(job_info["fonts"], [dict(name="Colonia", data_length=4)])
        self.assertEqual(job_info["fonts_skipped"], True)
        self.assertEqual(self.app.jobs_fonts[job_info["id"]], [font])
        self.assertEqual("fonts" in self.app.jobs["node"][0], False)

        # a job without fonts has no fonts to be skipped, whatever the node
        code, job_info = self._print(format="binie")
        self.assertEqual(code, 200)
        self.assertEqual("fonts_skipped" in job_info, False)
        self.app.jobs["node"].pop()

        self.app.nodes["node"] = dict(name="node")
        code, job_info = self._print(format="binie", fonts=[font])
        self.assertEqual(code, 200)
        self.assertEqual(job_info["fonts_skipped"], True)
        self.assertEqual("fonts" in self.app.jobs["node"][1], False)
        self.assertEqual(
            base64.b64decode(self.app.jobs["node"][1]["data_b64"]), b"Hello World"
        )

        # the fonts are sent to the node (not skipped) once it supports them
        self._node()
        code, job_info = self._print(format="binie", fonts=[font])
        self.assertEqual(code, 200)
        self.assertEqual("fonts_skipped" in job_info, False)
        self.assertEqual(self.app.jobs["node"][2]["fonts"], [font])

        # an unknown node (eg: not registered since the server restarted)
        # receives the fonts, that are skipped by the nodes that don't
        # support them, so that the nodes that support them use them
        code, job_info = self._print(
            url="/nodes/unknown/print", format="binie", fonts=[font]
        )
        self.assertEqual(code, 200)
        self.assertEqual("fonts_skipped" in job_info, False)
        self.assertEqual(self.app.jobs["unknown"][0]["fonts"], [font])

        # invalid fonts are still refused, whatever the node
        self.app.nodes["node"] = dict(name="node")
        code, result = self._print(format="binie", fonts=[dict(name="Colonia")])
        self.assertEqual(code, 400)
        code, result = self._print(format="pdf", fonts=[font])
        self.assertEqual(code, 400)
        self.assertEqual(len(self.app.jobs["node"]), 3)

    def test_print_default_fonts_type(self):
        # the jobs of the fonts type (as queued by the installation of the
        # fonts) require the node to support the fonts and have their payload
        # verified, even when they're sent to the print endpoint
        fonts = [dict(name="Colonia", data_b64="QUJD")]
        data = json.dumps(dict(fonts=fonts))
        code, result = self._print(data_b64=None, data=data, type="fonts")
        self.assertEqual(code, 409)
        self.assertEqual(
            result["message"], "Node 'node' doesn't support 'dynamic-fonts'"
        )

        self._node(capabilities=["npcolony", "binie", "xmpl"])
        code, result = self._print(data_b64=None, data=data, type="fonts")
        self.assertEqual(code, 409)

        self._node()
        invalid = [
            "Hello World",
            json.dumps(fonts),
            json.dumps(dict()),
            json.dumps(dict(fonts=[])),
            json.dumps(dict(fonts=dict(name="Colonia", data_b64="QUJD"))),
            json.dumps(dict(fonts=[dict(name="Colonia", md5="a" * 32)])),
        ]
        for value in invalid:
            code, result = self._print(data_b64=None, data=value, type="fonts")
            self.assertEqual(code, 400)
        self.assertEqual(
            result["message"],
            "Either data_b64 or url must be provided for font 'Colonia'",
        )
        code, result = self._print(type="fonts")
        self.assertEqual(result["message"], "Payload is not a valid fonts payload")
        self.assertEqual(self.app.jobs.get("node", []), [])

        # the job keeps the (light) information of the fonts, that are only
        # sent to the node in the payload of the job
        code, job_info = self._print(data_b64=None, data=data, type="fonts")
        self.assertEqual(code, 200)
        self.assertEqual(job_info["fonts"], [dict(name="Colonia", data_length=4)])
        self.assertEqual(self.app.jobs_fonts[job_info["id"]], None)
        job = self.app.jobs["node"][0]
        self.assertEqual("fonts" in job, False)
        self.assertEqual(
            json.loads(base64.b64decode(job["data_b64"]).decode("utf-8")),
            dict(fonts=fonts),
        )

    def test_print_default_fonts_dropped(self):
        # the fonts of the jobs are dropped together with the other (limited)
        # structures of the jobs, even when the later jobs have no fonts
        self.app.jobs_info = appier.LimitedSizeDict(max_size=2)
        self.app.jobs_data = appier.LimitedSizeDict(max_size=2)
        self.app.jobs_fonts = appier.LimitedSizeDict(max_size=2)
        self._node()
        fonts = [dict(name="Colonia", data_b64="QUJD")]
        code, first = self._print(format="binie", fonts=fonts)
        self.assertEqual(code, 200)
        self.assertEqual(self.app.jobs_fonts[first["id"]], fonts)
        for _index in range(2):
            code, job_info = self._print(format="binie")
            self.assertEqual(code, 200)
        self.assertEqual(first["id"] in self.app.jobs_data, False)
        self.assertEqual(first["id"] in self.app.jobs_fonts, False)
        self.assertEqual(
            sorted(self.app.jobs_fonts.keys()), sorted(self.app.jobs_data.keys())
        )

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

        # a document declaring fonts (with the ones of the request) is printed
        # by a node that doesn't support the fonts with its own fonts, the
        # fonts being marked as skipped (none of them sent to the node, the
        # declared ones being removed from the document sent to the node)
        declared = dict(name="Colonia", url="https://fonts.hive.pt/colonia.ttf")
        font = dict(name="Binaria", data_b64="QUJD")
        data = self._xmpl(fonts=[declared])
        code, job_info = self._print(
            data_b64=None, data=data, format="xmpl", fonts=[font]
        )
        self.assertEqual(code, 200)
        self.assertEqual(job_info["fonts_skipped"], True)
        job = self.app.jobs["node"].pop()
        self.assertEqual("fonts" in job, False)
        self.assertEqual(colony_print.xmpl_fonts(base64.b64decode(job["data_b64"])), [])
        self.assertEqual(
            base64.b64decode(self.app.jobs_data[job_info["id"]]), data.encode("utf-8")
        )

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
        self.assertEqual(self.app.jobs_fonts[job_info["id"]], None)

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

        # the XMPL documents are only printed by the npcolony engine, the
        # other engines would print the (XML) document as it is
        for type in ("text", "gravo", "fonts"):
            code, result = self._print(
                data_b64=None, data=self._xmpl(), type=type, format="xmpl"
            )
            self.assertEqual(code, 400)
            self.assertEqual(
                result["message"], "XMPL documents require the npcolony type"
            )

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

    def test_print_default_commands(self):
        # the commands for the node (eg: its restart) are only queued by
        # their own endpoints (that verify the node), so they're refused
        # as the type of a print request, even for a node that supports them
        self._node(capabilities=["npcolony", "restart", "update", "auto-update"])
        for type in ("restart", "update", "auto-update"):
            for url in ("/nodes/node/print", "/nodes/node/printers/receipt/print"):
                code, result = self._print(url=url, type=type)
                self.assertEqual(code, 400)
                self.assertEqual(
                    result["message"],
                    "Type '%s' is not valid for print requests" % type,
                )
        self.assertEqual(self.app.jobs.get("node", []), [])
        self.assertEqual(len(self.app.jobs_info), 0)

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

        # the fonts are skipped (not sent) for a node that doesn't support
        # them, that prints the document in the printer with its own fonts
        self._node(capabilities=["npcolony", "binie", "xmpl"])
        code, job_info = self._print(
            url="/nodes/node/printers/receipt/print", format="binie", fonts=fonts
        )
        self.assertEqual(code, 200)
        self.assertEqual(job_info["printer"], "receipt")
        self.assertEqual(job_info["fonts"], [dict(name="Colonia", data_length=4)])
        self.assertEqual(job_info["fonts_skipped"], True)
        self.assertEqual("fonts" in self.app.jobs["node"][2], False)
        self.assertEqual(self.app.jobs_fonts[job_info["id"]], fonts)

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
        self.assertEqual(
            job_info["fonts"],
            [
                dict(name="Colonia", data_length=4),
                dict(name="Binaria", url="https://fonts.hive.pt/binaria.ttf"),
            ],
        )
        self.assertEqual(self.app.jobs_fonts[job_info["id"]], None)
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

    def test_restart(self):
        response = self.app.post("/nodes/node/restart")
        self.assertEqual(response.code, 403)

        # the restart requires the capability of the node, which the nodes
        # that never registered and the older ones don't advertise
        code, result = self._print(url="/nodes/node/restart", data_b64=None)
        self.assertEqual(code, 409)
        self.assertEqual(result["message"], "Node 'node' doesn't support 'restart'")
        self._node(capabilities=["npcolony", "update", "auto-update"])
        code, result = self._print(url="/nodes/node/restart", data_b64=None)
        self.assertEqual(code, 409)
        self.app.nodes["node"] = dict(name="node")
        code, result = self._print(url="/nodes/node/restart", data_b64=None)
        self.assertEqual(code, 409)
        self.assertEqual(self.app.jobs.get("node", []), [])

        # the restart is queued as a job without data, for the node only
        self._node(capabilities=["npcolony", "restart", "update"])
        code, job_info = self._print(url="/nodes/node/restart", data_b64=None)
        self.assertEqual(code, 200)
        self.assertEqual(job_info["name"], "restart")
        self.assertEqual(job_info["type"], "restart")
        self.assertEqual(job_info["node_id"], "node")
        self.assertEqual(job_info["status"], "queued")
        self.assertEqual(job_info["data_length"], 0)
        self.assertEqual("options" in job_info, False)
        self.assertEqual(self.app.jobs_data[job_info["id"]], None)
        job = self.app.jobs["node"][0]
        self.assertEqual(job["id"], job_info["id"])
        self.assertEqual(job["type"], "restart")
        self.assertEqual("data_b64" in job, False)

        # a node with a restart (or an update) queued or in flight doesn't
        # get another one, the request returns that job
        code, other_info = self._print(url="/nodes/node/restart", data_b64=None)
        self.assertEqual(code, 200)
        self.assertEqual(other_info["id"], job_info["id"])
        code, other_info = self._print(url="/nodes/node/update", data_b64=None)
        self.assertEqual(code, 200)
        self.assertEqual(other_info["id"], job_info["id"])
        self.assertEqual(other_info["type"], "restart")
        self.assertEqual(len(self.app.jobs["node"]), 1)

        self._deliver()
        code, other_info = self._print(url="/nodes/node/restart", data_b64=None)
        self.assertEqual(other_info["id"], job_info["id"])
        self.assertEqual(other_info["status"], "printing")
        self.assertEqual(self.app.jobs.get("node", []), [])
        self.assertEqual(len(self.app.jobs_info), 1)

        # the restart of another node is not the one of the node
        self._node(id="other", capabilities=["restart"])
        code, other_info = self._print(url="/nodes/other/restart", data_b64=None)
        self.assertEqual(code, 200)
        self.assertEqual(other_info["node_id"], "other")
        self.assertEqual(other_info["id"] == job_info["id"], False)

        # the node is restarted again once the restart is finished (by the
        # server or by an error result of the node), and a queued restart
        # may be cancelled, as any other job
        self.app.jobs_info[job_info["id"]].update(status="finished")
        code, job_info = self._print(url="/nodes/node/restart", data_b64=None)
        self.assertEqual(code, 200)
        self.assertEqual(job_info["status"], "queued")
        self.assertEqual(len(self.app.jobs["node"]), 1)
        response = self.app.post(
            "/jobs/%s/cancel" % job_info["id"], headers=self.headers
        )
        self.assertEqual(response.code, 200)
        self.assertEqual(self.app.jobs["node"], [])
        code, other_info = self._print(url="/nodes/node/restart", data_b64=None)
        self.assertEqual(code, 200)
        self.assertEqual(other_info["id"] == job_info["id"], False)

    def test_restart_o(self):
        response = self.app.options("/nodes/node/restart")
        self.assertEqual(response.code, 200)
        self.assertEqual(
            response.headers["Access-Control-Allow-Origin"].startswith("*"), True
        )
        self.assertEqual(
            response.headers["Access-Control-Allow-Headers"].startswith("*"), True
        )

    def test_update(self):
        response = self.app.post("/nodes/node/update")
        self.assertEqual(response.code, 403)

        code, result = self._print(url="/nodes/node/update", data_b64=None)
        self.assertEqual(code, 409)
        self.assertEqual(result["message"], "Node 'node' doesn't support 'update'")

        # the node that is restarted from the admin is not updated from it
        # unless it's run by the boot (and advertises it)
        self._node(capabilities=["npcolony", "restart", "auto-update"])
        code, result = self._print(url="/nodes/node/update", data_b64=None)
        self.assertEqual(code, 409)
        self.assertEqual(self.app.jobs.get("node", []), [])

        self._node(capabilities=["npcolony", "restart", "update", "auto-update"])
        code, job_info = self._print(url="/nodes/node/update", data_b64=None)
        self.assertEqual(code, 200)
        self.assertEqual(job_info["name"], "update")
        self.assertEqual(job_info["type"], "update")
        self.assertEqual(job_info["status"], "queued")
        self.assertEqual(job_info["data_length"], 0)
        self.assertEqual("data_b64" in self.app.jobs["node"][0], False)

        # the update restarts the node, so the node doesn't get a restart
        # (nor another update) while it's queued or in flight
        for url in ("/nodes/node/update", "/nodes/node/restart"):
            code, other_info = self._print(url=url, data_b64=None)
            self.assertEqual(code, 200)
            self.assertEqual(other_info["id"], job_info["id"])
            self.assertEqual(other_info["type"], "update")
        self.assertEqual(len(self.app.jobs["node"]), 1)

    def test_update_o(self):
        response = self.app.options("/nodes/node/update")
        self.assertEqual(response.code, 200)
        self.assertEqual(
            response.headers["Access-Control-Allow-Origin"].startswith("*"), True
        )
        self.assertEqual(
            response.headers["Access-Control-Allow-Headers"].startswith("*"), True
        )

    def test_auto_update(self):
        response = self.app.post("/nodes/node/auto_update")
        self.assertEqual(response.code, 403)

        code, result = self._print(
            url="/nodes/node/auto_update", data_b64=None, enabled="0"
        )
        self.assertEqual(code, 409)
        self.assertEqual(result["message"], "Node 'node' doesn't support 'auto-update'")
        self._node(capabilities=["npcolony", "restart"])
        code, result = self._print(
            url="/nodes/node/auto_update", data_b64=None, enabled="0"
        )
        self.assertEqual(code, 409)

        # the auto-update must be explicitly enabled or disabled
        self._node(capabilities=["npcolony", "restart", "update", "auto-update"])
        for params in (dict(), dict(enabled="")):
            code, result = self._print(
                url="/nodes/node/auto_update", data_b64=None, **params
            )
            self.assertEqual(code, 400)
        self.assertEqual(self.app.jobs.get("node", []), [])

        code, job_info = self._print(
            url="/nodes/node/auto_update", data_b64=None, enabled="0"
        )
        self.assertEqual(code, 200)
        self.assertEqual(job_info["name"], "auto-update")
        self.assertEqual(job_info["type"], "auto-update")
        self.assertEqual(job_info["status"], "queued")
        self.assertEqual(job_info["data_length"], 0)
        self.assertEqual(job_info["options"], dict(enabled=False))
        job = self.app.jobs["node"][0]
        self.assertEqual(job["options"], dict(enabled=False))
        self.assertEqual("data_b64" in job, False)

        # the value is sent to the node as a boolean one, each request being
        # queued as a job of its own (the last one is the one that is kept)
        for value, enabled in (
            ("false", False),
            ("False", False),
            ("1", True),
            ("true", True),
            ("True", True),
        ):
            code, other_info = self._print(
                url="/nodes/node/auto_update", data_b64=None, enabled=value
            )
            self.assertEqual(code, 200)
            self.assertEqual(other_info["id"] == job_info["id"], False)
            self.assertEqual(other_info["options"], dict(enabled=enabled))
            self.assertEqual(self.app.jobs["node"][-1]["options"]["enabled"], enabled)
        self.assertEqual(len(self.app.jobs["node"]), 6)

        # the auto-update doesn't restart the node, so it's queued even
        # with a restart of the node pending (and doesn't prevent one)
        code, restart_info = self._print(url="/nodes/node/restart", data_b64=None)
        self.assertEqual(code, 200)
        self.assertEqual(restart_info["type"], "restart")
        code, other_info = self._print(
            url="/nodes/node/auto_update", data_b64=None, enabled="1"
        )
        self.assertEqual(code, 200)
        self.assertEqual(other_info["type"], "auto-update")
        self.assertEqual(len(self.app.jobs["node"]), 8)

    def test_auto_update_o(self):
        response = self.app.options("/nodes/node/auto_update")
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

    def test_command(self):
        controller = colony_print.controllers.NodeController(self.app)
        for type in ("restart", "update", "auto-update"):
            self.assertRaises(
                appier.OperationalError, lambda: controller._command("node", type)
            )
        self.assertEqual(len(self.app.jobs_info), 0)

        self._node(capabilities=["restart", "update", "auto-update"])
        job_info = controller._command("node", "restart")
        self.assertEqual(self.app.jobs_info[job_info["id"]] is job_info, True)
        self.assertEqual(
            dict((key, value) for key, value in job_info.items() if not "time" in key),
            dict(
                id=job_info["id"],
                name="restart",
                node_id="node",
                data_length=0,
                type="restart",
                status="queued",
            ),
        )
        self.assertEqual(controller._command("node", "restart") is job_info, True)
        self.assertEqual(controller._command("node", "update") is job_info, True)

        # only the jobs that restart the node (queued or in flight) prevent
        # another one, the other jobs of the node don't
        job_info.update(status="cancelled")
        self.app.jobs_info["print"] = dict(
            id="print", name="document", node_id="node", status="queued"
        )
        self.app.jobs_info["auto-update"] = dict(
            id="auto-update", node_id="node", type="auto-update", status="printing"
        )
        self.app.jobs_info["other"] = dict(
            id="other", node_id="other", type="restart", status="queued"
        )
        self.app.jobs_info["invalid"] = dict(id="invalid", node_id="node")
        other_info = controller._command("node", "update")
        self.assertEqual(other_info["type"], "update")
        self.assertEqual(other_info["id"] == job_info["id"], False)

        # the options of the command are part of its job
        options = dict(enabled=False)
        job_info = controller._command("node", "auto-update", options=options)
        self.assertEqual(job_info["options"], options)
        self.assertEqual(self.app.jobs["node"][-1]["options"], options)

    def test_finish_restart(self):
        controller = colony_print.controllers.NodeController(self.app)
        previous = dict(
            name="node",
            version="0.23.0",
            libraries=dict(appier="1.0.0"),
            start_time=100.0,
        )
        node = dict(
            name="node",
            version="0.24.0",
            libraries=dict(appier="1.1.0"),
            start_time=200.0,
            update=dict(auto=False, status="success", time=190.0),
        )

        def jobs():
            # builds the jobs of the node, one of each type that restarts
            # it in flight, and the ones that must never be finished
            self.app.jobs_info["restart"] = dict(
                id="restart", node_id="node", type="restart", status="printing"
            )
            self.app.jobs_info["update"] = dict(
                id="update", node_id="node", type="update", status="printing"
            )
            self.app.jobs_info["queued"] = dict(
                id="queued", node_id="node", type="restart", status="queued"
            )
            self.app.jobs_info["cancelled"] = dict(
                id="cancelled", node_id="node", type="update", status="cancelled"
            )
            self.app.jobs_info["auto-update"] = dict(
                id="auto-update", node_id="node", type="auto-update", status="printing"
            )
            self.app.jobs_info["print"] = dict(
                id="print", node_id="node", status="printing"
            )
            self.app.jobs_info["other"] = dict(
                id="other", node_id="other", type="restart", status="printing"
            )
            self.app.jobs_info["invalid"] = dict(id="invalid")

        def statuses():
            return dict(
                (id, job_info.get("status", None))
                for id, job_info in self.app.jobs_info.items()
            )

        # the node that was not restarted (first registration, no previous
        # start time or the same start time) has no job finished
        jobs()
        unchanged = statuses()
        controller._finish_restart("node", None, node)
        controller._finish_restart("node", dict(name="node"), node)
        controller._finish_restart("node", previous, dict(node, start_time=100.0))
        controller._finish_restart("node", dict(name="node"), dict(name="node"))
        controller._finish_restart("node", dict(), dict())
        self.assertEqual(statuses(), unchanged)

        # only the jobs in flight that restart the (restarted) node are
        # finished, with the versions of the node before and after and, for
        # the update, with the outcome of the update run by its boot
        controller._finish_restart("node", previous, node)
        self.assertEqual(
            statuses(), dict(unchanged, restart="finished", update="finished")
        )
        before = dict(
            version="0.23.0", libraries=dict(appier="1.0.0"), start_time=100.0
        )
        after = dict(version="0.24.0", libraries=dict(appier="1.1.0"), start_time=200.0)
        job_info = self.app.jobs_info["restart"]
        self.assertEqual(type(job_info["finish_time"]), float)
        self.assertEqual(
            job_info["result"],
            dict(result="success", handler="restart", before=before, after=after),
        )
        self.assertEqual(
            self.app.jobs_info["update"]["result"],
            dict(
                result="success",
                handler="update",
                before=before,
                after=after,
                update=dict(auto=False, status="success", time=190.0),
            ),
        )
        self.assertEqual("result" in self.app.jobs_info["queued"], False)

        # the update that fails finishes its job as an error (with the
        # error of the update), the node being restarted anyway
        update = dict(auto=True, status="failure", time=190.0, error="No index")
        jobs()
        controller._finish_restart("node", previous, dict(node, update=update))
        result = self.app.jobs_info["update"]["result"]
        self.assertEqual(result["result"], "error")
        self.assertEqual(result["error"], "No index")
        self.assertEqual(result["update"], update)
        self.assertEqual(result["after"], after)
        self.assertEqual(self.app.jobs_info["restart"]["result"]["result"], "success")
        self.assertEqual("error" in self.app.jobs_info["restart"]["result"], False)

        # the same happens when the update was not run by the boot (eg:
        # told to skip it) or its outcome is not known
        for update in (dict(auto=False, status="skipped", time=190.0), dict(), None):
            jobs()
            controller._finish_restart("node", previous, dict(node, update=update))
            result = self.app.jobs_info["update"]["result"]
            self.assertEqual(result["result"], "error")
            self.assertEqual(result["error"], "Update not run by the node")
            self.assertEqual(result["update"], update or dict())

        # the start times are not compared, as a restarted node may report
        # an older one (the clock of its machine going back) or none at all
        # (rolled back to an older version), its jobs being finished anyway
        jobs()
        controller._finish_restart("node", previous, dict(node, start_time=50.0))
        self.assertEqual(
            statuses(), dict(unchanged, restart="finished", update="finished")
        )
        result = self.app.jobs_info["restart"]["result"]
        self.assertEqual(result["result"], "success")
        self.assertEqual(result["after"]["start_time"], 50.0)

        jobs()
        older = dict(name="node", version="0.23.0", libraries=dict(appier="1.0.0"))
        controller._finish_restart("node", previous, older)
        self.assertEqual(
            statuses(), dict(unchanged, restart="finished", update="finished")
        )
        result = self.app.jobs_info["restart"]["result"]
        self.assertEqual(result["result"], "success")
        self.assertEqual(
            result["after"],
            dict(version="0.23.0", libraries=dict(appier="1.0.0"), start_time=None),
        )
        result = self.app.jobs_info["update"]["result"]
        self.assertEqual(result["result"], "error")
        self.assertEqual(result["error"], "Update not run by the node")

        # the versions that are not known (eg: not reported by the node)
        # are kept as invalid values
        jobs()
        controller._finish_restart(
            "node", dict(start_time=100.0), dict(start_time=200.0)
        )
        self.assertEqual(
            self.app.jobs_info["restart"]["result"],
            dict(
                result="success",
                handler="restart",
                before=dict(version=None, libraries=None, start_time=100.0),
                after=dict(version=None, libraries=None, start_time=200.0),
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
        self.assertEqual(
            controller._verify_fonts(
                "other",
                data_b64,
                format="binie",
                fonts=[dict(name="Colonia", md5="a" * 32)],
            ),
            [dict(name="Colonia", md5="a" * 32)],
        )

        # the fonts and the XMPL documents are only valid for the jobs of
        # the npcolony type (the default one)
        self.assertEqual(
            controller._verify_fonts("node", data_b64, type="npcolony", format="xmpl"),
            [dict(name="Colonia", md5="a" * 32)],
        )
        self.assertRaises(
            appier.OperationalError,
            lambda: controller._verify_fonts(
                "node", data_b64, type="text", format="xmpl"
            ),
        )
        self.assertRaises(
            appier.OperationalError,
            lambda: controller._verify_fonts(
                "node",
                data_b64,
                type="gravo",
                format="binie",
                fonts=[dict(name="Colonia", md5="a" * 32)],
            ),
        )

        # the payload of the jobs of the fonts type holds the fonts to be
        # installed by the node, that can't be references (by MD5 alone)
        fonts = [dict(name="Colonia", style="bold", url="https://fonts.hive.pt/c.ttf")]
        payload = base64.b64encode(json.dumps(dict(fonts=fonts)).encode("utf-8"))
        self.assertEqual(controller._verify_fonts("node", payload, type="fonts"), fonts)
        self.assertRaises(
            appier.OperationalError,
            lambda: controller._verify_fonts("other", payload, type="fonts"),
        )
        self.assertRaises(
            appier.OperationalError,
            lambda: controller._verify_fonts("node", data_b64, type="fonts"),
        )
        payload = base64.b64encode(
            json.dumps(dict(fonts=[dict(name="Colonia", md5="a" * 32)])).encode("utf-8")
        )
        self.assertRaises(
            appier.OperationalError,
            lambda: controller._verify_fonts("node", payload, type="fonts"),
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
