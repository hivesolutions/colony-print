#!/usr/bin/python
# -*- coding: utf-8 -*-

import json

import appier

class NodeController(appier.Controller):

    @appier.route("/nodes", "GET", json = True)
    def list(self):
        return self.owner.nodes

    @appier.route("/nodes/<str:id>", "POST", json = True)
    def create(self, id):
        node = appier.get_object()
        self.owner.nodes[id] = node

    @appier.route("/nodes/<str:id>", "GET", json = True)
    def show(self, id, printer):
        return self.owner.nodes[id]

    @appier.route("/nodes/<str:id>/jobs", "GET", json = True)
    def jobs(self, id):
        self.request.set_content_type("application/json")
        yield -1
        yield appier.ensure_async(self.gen_wait_jobs(id))

    @appier.route("/nodes/<str:id>/printers/<str:printer>/print", ("GET", "POST"), json = True)
    def print_document(self, id, printer):
        job = appier.get_object()
        job["printer"] = printer
        jobs = self.owner.jobs.get(id, [])
        jobs.append(job)
        self.owner.jobs[id] = jobs

    def gen_wait_jobs(self, id):

        @appier.coroutine
        def wait_jobs(future):
            while True:
                jobs = self.owner.jobs.pop(id, [])
                if jobs: break
                for value in appier.sleep(1.0): yield value
            jobs_s = json.dumps(jobs)
            future.set_result(jobs_s)

        return wait_jobs
