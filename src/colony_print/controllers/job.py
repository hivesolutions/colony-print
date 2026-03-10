#!/usr/bin/python
# -*- coding: utf-8 -*-

import os

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
