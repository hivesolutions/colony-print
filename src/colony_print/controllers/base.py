#!/usr/bin/python
# -*- coding: utf-8 -*-

import appier

class BaseController(appier.Controller):

    @appier.controller("BaseController")
    def __init__(self, owner, *args, **kwargs):
        appier.Controller.__init__(self, owner, *args, **kwargs)

    @appier.route("/print/win32", "POST")
    def print_win32(self):
        return self.template(
            "account/new.html.tpl",
            account = {},
            errors = {}
        )
