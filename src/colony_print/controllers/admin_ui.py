#!/usr/bin/python
# -*- coding: utf-8 -*-

import os

import appier

ADMIN_UI_PREFIX = "admin-ui"
""" The prefix path for the Admin UI static files,
relative to the application's static directory """


class AdminUIController(appier.Controller):
    """
    Controller responsible for serving the Colony Print
    Admin UI single page application (SPA) built with
    React and TypeScript.

    The built static files are expected to be located in
    the `static/admin-ui` directory within the package.
    """

    @appier.route("/admin-ui", "GET")
    def admin_ui(self):
        return self._serve_index()

    @appier.route("/admin-ui/<regex('.+'):path>", "GET")
    def admin_ui_path(self, path):
        # tries to serve the requested static file and if
        # it does not exist falls back to the index file
        # to support client-side routing
        resource = os.path.join(ADMIN_UI_PREFIX, path)
        static_path = os.path.join(self.owner.static_path, resource)
        if os.path.isfile(static_path):
            return self.send_static(resource, cache=True)
        return self._serve_index()

    def _serve_index(self):
        """
        Serves the main `index.html` file for the SPA,
        this is the entry point for the admin UI application.

        :rtype: String
        :return: The contents of the index HTML file.
        """

        resource = os.path.join(ADMIN_UI_PREFIX, "index.html")
        static_path = os.path.join(self.owner.static_path, resource)
        if not os.path.isfile(static_path):
            raise appier.NotFoundError(message="Admin UI not built")
        return self.send_static(resource)
