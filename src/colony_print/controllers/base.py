#!/usr/bin/python
# -*- coding: utf-8 -*-

import appier

import webook

class BaseController(appier.Controller):

    @appier.controller("BaseController")
    def __init__(self, owner, *args, **kwargs):
        appier.Controller.__init__(self, owner, *args, **kwargs)

    @appier.route("/accounts/new", "GET")
    def new(self):
        return self.template(
            "account/new.html.tpl",
            account = {},
            errors = {}
        )

    @appier.route("/accounts", "POST")
    def create(self):
        account = webook.Account.new()
        try: account.save()
        except appier.ValidationError, error:
            return self.template(
                "account/new.html.tpl",
                account = error.model,
                errors = error.errors
            )

        # redirects the user to the show page of the account that
        # was just created (using named based redirection)
        return self.redirect(
            self.url_for("account.show", username = account.username)
        )

    @appier.route("/accounts/<str:username>", "GET")
    def show(self, username):
        account = webook.Account.get(username = username)
        return self.template(
            "account/show.html.tpl",
            account = account
        )
