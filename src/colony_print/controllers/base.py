#!/usr/bin/python
# -*- coding: utf-8 -*-

import time

import appier


class BaseController(appier.Controller):
    @appier.route("/ping", "GET", json=True)
    def ping(self):
        return dict(time=time.time())
