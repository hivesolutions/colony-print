#!/usr/bin/python
# -*- coding: utf-8 -*-

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
