#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import time

import appier


class JobController(appier.Controller):
    @appier.route("/jobs", "GET", json=True)
    @appier.ensure(token="admin")
    def list(self):
        return dict(self.owner.jobs_info)

    @appier.route("/jobs/<str:id>", "GET", json=True)
    @appier.ensure(token="admin")
    def show(self, id):
        return self.owner.jobs_info[id]

    @appier.route("/jobs/<str:id>/cancel", "POST", json=True)
    @appier.ensure(token="admin")
    def cancel(self, id):
        appier.verify(
            id in self.owner.jobs_info,
            message="Job not found",
            code=404,
        )

        job_info = self.owner.jobs_info[id]
        status = job_info.get("status", None)

        # only queued jobs may be reliably cancelled, as a job already
        # picked up by a node is being printed and can no longer be
        # stopped from the server side
        appier.verify(
            status == "queued",
            message="Job in '%s' status can not be cancelled" % status,
            code=409,
        )

        # removes the job from the pending queue of its node so that it
        # is never dispatched, in case it has not been picked up yet
        node_id = job_info["node_id"]
        jobs = self.owner.jobs.get(node_id, [])
        self.owner.jobs[node_id] = [job for job in jobs if not job["id"] == id]

        job_info.update(status="cancelled", cancel_time=time.time())
        return job_info

    @appier.route("/jobs/<str:id>/files", "GET", json=True)
    @appier.ensure(token="admin")
    def files(self, id):
        data_path = appier.conf("DATA_PATH", "./data")
        job_path = os.path.join(data_path, id)
        if not os.path.isdir(job_path):
            return []
        return [
            dict(name=name, size=os.path.getsize(os.path.join(job_path, name)))
            for name in sorted(os.listdir(job_path))
        ]

    @appier.route("/jobs/<str:id>/files/<str:name>", "GET")
    @appier.ensure(token="admin")
    def file(self, id, name):
        data_path = appier.conf("DATA_PATH", "./data")
        file_path = os.path.join(data_path, id, name)
        appier.verify(
            os.path.isfile(file_path),
            message="File not found",
            code=404,
        )
        return self.send_path(file_path)
