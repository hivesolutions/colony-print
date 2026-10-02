#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import json
import uuid
import time
import base64

import appier

HELLO_WORLD_B64 = "SGVsbG8gV29ybGQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAQAAAAEAAABAAQAAAA\
AAAAAAAABDYWxpYnJpAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\
AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAACQAAAAMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\
AAAAAAAAAwAAABIZWxsbyBXb3JsZAA="

VALID_OPTIONS = set(
    [
        "scale",
        "quality",
        "media",
        "scaling",
        "save_output",
        "send_email",
        "email_address",
        "email_receivers",
        "email_receiver",
        "email_override",
    ]
)

FONT_INFO_FIELDS = set(["name", "style", "url", "md5"])
""" The set of fields of the fonts of a job that are kept in the
information of the job, the (heavy) data of the fonts is not """

FONT_FORMATS = set(["binie", "xmpl"])
""" The set of formats of the documents that may be printed
with fonts installed on demand (sent in the print request) """


class NodeController(appier.Controller):
    @appier.route("/nodes", "GET", json=True)
    @appier.ensure(token="admin")
    def list(self):
        return self.owner.nodes

    @appier.route("/nodes/<str:id>", "POST", json=True)
    @appier.ensure(token="admin")
    def create(self, id):
        node = appier.get_object()
        node["last_ping"] = time.time()
        self.owner.nodes[id] = node

    @appier.route("/nodes/<str:id>", "GET", json=True)
    @appier.ensure(token="admin")
    def show(self, id):
        return self.enrich_node(id, self.owner.nodes[id])

    @appier.route("/nodes/<str:id>/jobs", "GET", json=True)
    @appier.ensure(token="admin")
    def jobs(self, id):
        self.request.set_content_type("application/json")
        for value in appier.header_a():
            yield value
        for value in self.wait_jobs(id):
            yield value

    @appier.route("/nodes/<str:id>/jobs_peek", "GET", json=True)
    @appier.ensure(token="admin")
    def jobs_peek(self, id):
        jobs = self.owner.jobs.get(id, [])
        return jobs

    @appier.route("/nodes/<str:id>/jobs/<str:job_id>/result", "POST", json=True)
    @appier.ensure(token="admin")
    def job_result(self, id, job_id):
        data_path = appier.conf("DATA_PATH", "./data")
        job_path = os.path.join(data_path, job_id)

        payload = appier.get_object()
        data = payload.get("data", dict())
        files = data.pop("files", [])

        job_info = self.owner.jobs_info[job_id]
        if not id == job_info["node_id"]:
            raise appier.OperationalError("Node ID mismatch")

        if (payload or files) and not os.path.exists(job_path):
            os.makedirs(job_path)

        if payload:
            payload_s = json.dumps(payload).encode("utf-8")
            with open(os.path.join(job_path, "payload.json"), "wb") as _file:
                _file.write(payload_s)

        for file in files:
            _file = appier.File(file)
            _file.save(path=os.path.join(job_path, _file.file_name))

        job_info.update(status="finished", finish_time=time.time(), result=payload)

    @appier.route("/nodes/<str:id>/print", ("GET", "POST"), json=True)
    @appier.ensure(token="admin")
    def print_default(self, id):
        data = self.field("data", None)
        data_b64 = self.field("data_b64", None)
        name = self.field("name", None)
        type = self.field("type", None)
        format = self.field("format", None)
        options = self.field("options", None, cast=dict)
        fonts = self.field("fonts", None, cast=json.loads)

        appier.verify(
            data or data_b64,
            message="Either data or data_b64 fields must be provided",
            code=400,
        )
        appier.verify(
            not (data and data_b64),
            message="Only one of data or data_b64 fields must be provided",
            code=400,
        )

        job_id = str(uuid.uuid4())
        name = name or job_id
        if data:
            data_b64 = base64.b64encode(
                appier.legacy.bytes(data, encoding="utf-8")
            ).decode("utf-8")
        fonts_info = self._verify_fonts(id, data_b64, format=format, fonts=fonts)

        job_info = dict(id=job_id, name=name, node_id=id, data_length=len(data_b64))
        if type:
            job_info["type"] = type
        if format:
            job_info["format"] = format
        if options:
            job_info["options"] = dict(
                (k, v) for k, v in options.items() if k in VALID_OPTIONS
            )
        if fonts_info:
            job_info["fonts"] = fonts_info
        self.owner.jobs_info[job_id] = job_info
        self.owner.jobs_data[job_id] = data_b64
        if fonts:
            self.owner.jobs_fonts[job_id] = fonts

        # creates a copy of the job info as starting
        # point for the job structure and then adds
        # the "heavy" data (base64 encoded) to it, with
        # the fonts of the request replacing their (light)
        # information, as the node installs them
        job = dict(job_info)
        job["data_b64"] = data_b64
        job.pop("fonts", None)
        if fonts:
            job["fonts"] = fonts
        jobs = self.owner.jobs.get(id, [])
        jobs.append(job)
        self.owner.jobs[id] = jobs
        appier.notify("jobs:%s" % id)

        job_info.update(status="queued", queued_time=time.time())
        return job_info

    @appier.route("/nodes/<str:id>/print", "OPTIONS")
    def print_default_o(self, id):
        return ""

    @appier.route("/nodes/<str:id>/print_hello", ("GET", "POST"), json=True)
    @appier.ensure(token="admin")
    def print_hello_default(self, id):
        self.set_field("data_b64", HELLO_WORLD_B64)
        self.set_field("name", "hello_world")
        return self.print_default(id)

    @appier.route("/nodes/<str:id>/printers/print", ("GET", "POST"), json=True)
    @appier.ensure(token="admin")
    def print_printer_f(self, id):
        printer = self.field("printer")
        return self.print_printer(id, printer)

    @appier.route("/nodes/<str:id>/printers/print", "OPTIONS")
    def print_printer_of(self, id):
        printer = self.field("printer")
        return self.print_printer_o(id, printer)

    @appier.route("/nodes/<str:id>/printers/print_hello", ("GET", "POST"), json=True)
    @appier.ensure(token="admin")
    def print_hello_printer_f(self, id):
        printer = self.field("printer")
        return self.print_hello_printer(id, printer)

    @appier.route(
        "/nodes/<str:id>/printers/<str:printer>/print", ("GET", "POST"), json=True
    )
    @appier.ensure(token="admin")
    def print_printer(self, id, printer):
        data = self.field("data", None)
        data_b64 = self.field("data_b64", None)
        name = self.field("name", None)
        type = self.field("type", None)
        format = self.field("format", None)
        options = self.field("options", None, cast=dict)
        fonts = self.field("fonts", None, cast=json.loads)

        appier.verify(
            data or data_b64,
            message="Either data or data_b64 fields must be provided",
            code=400,
        )
        appier.verify(
            not (data and data_b64),
            message="Only one of data or data_b64 fields must be provided",
            code=400,
        )

        job_id = str(uuid.uuid4())
        name = name or job_id
        if data:
            data_b64 = base64.b64encode(
                appier.legacy.bytes(data, encoding="utf-8")
            ).decode("utf-8")
        fonts_info = self._verify_fonts(id, data_b64, format=format, fonts=fonts)

        job_info = dict(
            id=job_id, name=name, node_id=id, printer=printer, data_length=len(data_b64)
        )
        if type:
            job_info["type"] = type
        if format:
            job_info["format"] = format
        if options:
            job_info["options"] = dict(
                (k, v) for k, v in options.items() if k in VALID_OPTIONS
            )
        if fonts_info:
            job_info["fonts"] = fonts_info
        self.owner.jobs_info[job_id] = job_info
        self.owner.jobs_data[job_id] = data_b64
        if fonts:
            self.owner.jobs_fonts[job_id] = fonts

        # creates a copy of the job info as starting
        # point for the job structure and then adds
        # the "heavy" data (base64 encoded) to it, with
        # the fonts of the request replacing their (light)
        # information, as the node installs them
        job = dict(job_info)
        job["data_b64"] = data_b64
        job.pop("fonts", None)
        if fonts:
            job["fonts"] = fonts
        jobs = self.owner.jobs.get(id, [])
        jobs.append(job)
        self.owner.jobs[id] = jobs
        appier.notify("jobs:%s" % id)

        job_info.update(status="queued", queued_time=time.time())
        return job_info

    @appier.route("/nodes/<str:id>/printers/<str:printer>/print", "OPTIONS")
    def print_printer_o(self, id, printer):
        return ""

    @appier.route(
        "/nodes/<str:id>/printers/<str:printer>/print_hello", ("GET", "POST"), json=True
    )
    @appier.ensure(token="admin")
    def print_hello_printer(self, id, printer):
        self.set_field("data_b64", HELLO_WORLD_B64)
        self.set_field("name", "hello_world")
        return self.print_printer(id, printer)

    @appier.route("/nodes/<str:id>/fonts", "GET", json=True)
    @appier.ensure(token="admin")
    def fonts(self, id):
        self._ensure_capability(id, "dynamic-fonts")
        return self.owner.nodes[id].get("fonts", [])

    @appier.route("/nodes/<str:id>/fonts", "POST", json=True)
    @appier.ensure(token="admin")
    def install_fonts(self, id):
        import colony_print

        fonts = self.field("fonts", None, cast=json.loads)
        appier.verify(
            fonts and isinstance(fonts, list),
            message="List of fonts must be provided",
            code=400,
        )
        for font in fonts:
            colony_print.verify_font(font, reference=False)
        self._ensure_capability(id, "dynamic-fonts")

        # sends the fonts to the node as a job of the fonts type, whose
        # (JSON) payload contains the fonts to be installed by the node
        self.set_field("data", json.dumps(dict(fonts=fonts)))
        self.set_field("data_b64", None)
        self.set_field("name", self.field("name", "fonts"))
        self.set_field("type", "fonts")
        self.set_field("format", None)
        self.set_field("fonts", None)
        return self.print_default(id)

    @appier.route("/nodes/<str:id>/fonts", "OPTIONS")
    def fonts_o(self, id):
        return ""

    @appier.coroutine
    def wait_jobs(self, id):
        while True:
            jobs = self.owner.jobs.pop(id, [])
            if jobs:
                break
            for value in appier.wait("jobs:%s" % id):
                yield value
        yield json.dumps(jobs)
        for job in jobs:
            job_id = job["id"]
            if not job_id in self.owner.jobs_info:
                continue
            job_info = self.owner.jobs_info[job_id]
            job_info.update(status="printing", printing_time=time.time())

    def enrich_node(self, id, node):
        # enriches a copy of the provided node with the print statistics
        # computed on demand from the jobs retained by the server, so that
        # they are not kept within the (stored) node, the one submitted by
        # the node itself, which is left untouched
        node = dict(node)
        node["stats"] = self.owner.node_stats(id)
        return node

    def _verify_fonts(self, id, data_b64, format=None, fonts=None):
        """
        Verifies the fonts of a print job, the ones of the print request
        and the ones declared by its document (for XMPL documents), and
        that the node supports them, raising an exception otherwise.

        XMPL documents are verified (converted as the node does) so that
        invalid documents are refused before being sent to the node.

        :type id: String
        :param id: The identifier of the node of the job.
        :type data_b64: String
        :param data_b64: The base64 encoded document of the job.
        :type format: String
        :param format: The format of the document of the job, if any.
        :type fonts: List
        :param fonts: The fonts (entries) of the print request, if any.
        :rtype: List
        :return: The (light) information of the fonts of the job, the
        ones of the request and the ones declared by the document.
        """

        import colony_print

        # verifies the fonts of the print request, that are only valid for
        # the documents of the formats that may be printed with them
        if fonts:
            appier.verify(
                isinstance(fonts, list),
                message="Fonts must be a list",
                code=400,
            )
            appier.verify(
                format in FONT_FORMATS,
                message="Fonts require one of the formats %s" % sorted(FONT_FORMATS),
                code=400,
            )
            for font in fonts:
                colony_print.verify_font(font)

        # verifies that XMPL documents are supported by the node and that
        # the document is valid, retrieving the fonts it declares
        declared = []
        if format == "xmpl":
            self._ensure_capability(id, "xmpl")
            try:
                data = base64.b64decode(data_b64)
                declared = colony_print.xmpl_fonts(data)
                self._verify_xmpl(data)
            except appier.OperationalError:
                raise
            except Exception:
                raise appier.OperationalError(
                    message="Document is not a valid XMPL document", code=400
                )
            for font in declared:
                colony_print.verify_font(font)

        # builds the information of the fonts without their (heavy) data
        # and verifies that the node supports the fonts (if any)
        fonts_info = []
        for font in declared + (fonts or []):
            font_info = dict((k, v) for k, v in font.items() if k in FONT_INFO_FIELDS)
            if "data_b64" in font:
                font_info["data_length"] = len(font["data_b64"])
            fonts_info.append(font_info)
        if fonts_info:
            self._ensure_capability(id, "dynamic-fonts")
        return fonts_info

    def _verify_xmpl(self, data):
        """
        Verifies that the provided data is a valid XMPL document, with a
        printing document as its root element and only inline images, that
        is converted into a binie document (as the node does), raising an
        exception otherwise.

        :type data: String
        :param data: The XMPL document to be verified.
        :see: https://github.com/hivesolutions/colony-print/blob/master/doc/xmpl.md
        """

        import colony_print

        # verifies that the document may be printed by a node (its root
        # element and its images) and then converts the document into binie
        colony_print.verify_xmpl(data)
        manager = colony_print.PrintingManager()
        manager.load()
        manager.print_language(data, dict(name="binie", file=appier.legacy.BytesIO()))

    def _ensure_capability(self, id, capability):
        """
        Ensures that the node with the provided identifier supports the
        provided capability, as advertised by the node, raising an
        exception otherwise (as when the node is unknown).

        :type id: String
        :param id: The identifier of the node.
        :type capability: String
        :param capability: The name of the capability (eg: xmpl).
        :see: https://github.com/hivesolutions/colony-print/blob/master/doc/capabilities.md
        """

        node = self.owner.nodes.get(id, dict())
        appier.verify(
            capability in node.get("capabilities", []),
            message="Node '%s' doesn't support '%s'" % (id, capability),
            code=409,
        )
