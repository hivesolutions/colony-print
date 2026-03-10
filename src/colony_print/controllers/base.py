#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import time

import appier


class BaseController(appier.Controller):
    @appier.route("/ping", "GET", json=True)
    def ping(self):
        return dict(time=time.time())

    @appier.route("/info", "GET", json=True)
    @appier.ensure(token="admin")
    def info(self):
        uptime = (
            time.time() - self.owner.start_time
            if hasattr(self.owner, "start_time")
            else None
        )
        return dict(
            name=self.owner.name,
            version=self.owner._version(),
            description=self.owner._description(),
            platform=appier.PLATFORM,
            os=os.name,
            python=sys.version,
            uptime=uptime,
            nodes=len(self.owner.nodes),
            jobs=len(self.owner.jobs_info),
        )
