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
        "email_address",
        "email_receivers",
        "email_receiver",
        "email_override",
    ]
)


class NodeController(appier.Controller):
    @appier.route("/nodes", "GET", json=True)
    @appier.ensure(token="admin")
    def list(self):
        return self.owner.nodes

    @appier.route("/nodes/<str:id>", "POST", json=True)
    @appier.ensure(token="admin")
    def create(self, id):
        node = appier.get_object()
        self.owner.nodes[id] = node

    @appier.route("/nodes/<str:id>", "GET", json=True)
    @appier.ensure(token="admin")
    def show(self, id):
        return self.owner.nodes[id]

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

        job_info = dict(id=job_id, name=name, node_id=id, data_length=len(data_b64))
        if type:
            job_info["type"] = type
        if format:
            job_info["format"] = format
        if options:
            job_info["options"] = dict(
                (k, v) for k, v in options.items() if k in VALID_OPTIONS
            )
        self.owner.jobs_info[job_id] = job_info

        # creates a copy of the job info as starting
        # point for the job structure and then adds
        # the "heavy" data (base64 encoded) to it
        job = dict(job_info)
        job["data_b64"] = data_b64
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
        self.owner.jobs_info[job_id] = job_info

        # creates a copy of the job info as starting
        # point for the job structure and then adds
        # the "heavy" data (base64 encoded) to it
        job = dict(job_info)
        job["data_b64"] = data_b64
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
            job_info = self.owner.jobs_info[job["id"]]
            job_info.update(status="printing", printing_time=time.time())
