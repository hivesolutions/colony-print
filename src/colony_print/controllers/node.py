#!/usr/bin/python
# -*- coding: utf-8 -*-

import json

import appier

class NodeController(appier.Controller):

    @appier.route("/nodes", "GET", json = True)
    @appier.ensure(token = "admin")
    def list(self):
        return self.owner.nodes

    @appier.route("/nodes/<str:id>", "POST", json = True)
    @appier.ensure(token = "admin")
    def create(self, id):
        node = appier.get_object()
        self.owner.nodes[id] = node

    @appier.route("/nodes/<str:id>", "GET", json = True)
    @appier.ensure(token = "admin")
    def show(self, id):
        return self.owner.nodes[id]

    @appier.route("/nodes/<str:id>/jobs", "GET", json = True)
    @appier.ensure(token = "admin")
    def jobs(self, id):
        self.request.set_content_type("application/json")
        for value in appier.header_a(): yield value
        for value in self.wait_jobs(id): yield value

    @appier.route("/nodes/<str:id>/jobs_peek", "GET", json = True)
    @appier.ensure(token = "admin")
    def jobs_peek(self, id):
        jobs = self.owner.jobs.get(id, [])
        return jobs

    @appier.route("/nodes/<str:id>/print", ("GET", "POST"), json = True)
    @appier.ensure(token = "admin")
    def print_default(self, id):
        data_b64 = self.field("data_b64", mandatory = True, not_empty = True)
        name = self.field("name", None)
        job = dict(data_b64 = data_b64)
        if name: job["name"] = name
        jobs = self.owner.jobs.get(id, [])
        jobs.append(job)
        self.owner.jobs[id] = jobs
        appier.notify("jobs:%s" % id)

    @appier.route("/nodes/<str:id>/print", "OPTIONS")
    def print_default_o(self, id):
        return ""

    @appier.route("/nodes/<str:id>/printers/<str:printer>/print", ("GET", "POST"), json = True)
    @appier.ensure(token = "admin")
    def print_printer(self, id, printer):
        data_b64 = self.field("data_b64", mandatory = True, not_empty = True)
        name = self.field("name", None)
        job = dict(
            data_b64 = data_b64,
            printer = printer
        )
        if name: job["name"] = name
        jobs = self.owner.jobs.get(id, [])
        jobs.append(job)
        self.owner.jobs[id] = jobs
        appier.notify("jobs:%s" % id)

    @appier.route("/nodes/<str:id>/printers/<str:printer>/print", "OPTIONS")
    def print_printer_o(self, id, printer):
        return ""

    @appier.coroutine
    def wait_jobs(self, id):
        while True:
            jobs = self.owner.jobs.pop(id, [])
            if jobs: break
            for value in appier.wait("jobs:%s" % id): yield value
        yield json.dumps(jobs)
