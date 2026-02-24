#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import mimetypes

import appier


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

    @appier.route("/admin-ui/<path:path>", "GET")
    def admin_ui_path(self, path):
        # tries to serve the requested static file and if
        # it does not exist falls back to the index file
        # to support client-side routing
        static_path = self._resolve_path(path)
        if os.path.isfile(static_path):
            return self._serve_file(static_path)
        return self._serve_index()

    def _serve_index(self):
        """
        Serves the main `index.html` file for the SPA,
        this is the entry point for the admin UI application.

        :rtype: String
        :return: The contents of the index HTML file.
        """

        index_path = self._resolve_path("index.html")
        if not os.path.isfile(index_path):
            raise appier.NotFoundError(message="Admin UI not built")
        return self._serve_file(index_path)

    def _serve_file(self, path):
        """
        Serves a static file from the given absolute path,
        setting the appropriate content type header based
        on the file extension.

        :type path: String
        :param path: The absolute path to the file to serve.
        :rtype: String
        :return: The contents of the file.
        """

        mime, _encoding = mimetypes.guess_type(path)
        if mime:
            self.content_type(mime)
        file = open(path, "rb")
        try:
            contents = file.read()
        finally:
            file.close()
        return contents

    def _resolve_path(self, path):
        """
        Resolves the given relative path to an absolute path
        within the `static/admin-ui` directory.

        :type path: String
        :param path: The relative path to resolve.
        :rtype: String
        :return: The absolute path to the file.
        """

        base_path = os.path.dirname(os.path.dirname(__file__))
        return os.path.join(base_path, "static", "admin-ui", path)
