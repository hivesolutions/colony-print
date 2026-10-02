#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import json
import shutil
import hashlib
import logging
import tempfile
import unittest

import appier

import colony_print

WHEEL_NAME = "colony_print-0.21.0-py2.py3-none-any.whl"
""" The (file) name of the wheel package used in the tests """

NATIVE_NAME = "npcolony-1.3.0-cp314-cp314-win_amd64.whl"
""" The (file) name of a native wheel package used in the tests """

BOUNDARY = "colony-print-boundary"
""" The boundary used in the multipart requests of the tests """

PACKAGES_KEY = "colony-print-packages"
""" The packages key, that allows the publishing of packages,
used in the tests """


class PackageControllerTest(unittest.TestCase):
    def setUp(self):
        self.packages_path = tempfile.mkdtemp(prefix="colony-print-packages-test-")
        appier.conf_s("PACKAGES_PATH", self.packages_path)
        appier.conf_s("PACKAGES_KEY", PACKAGES_KEY)
        self.app = colony_print.ColonyPrintApp(level=logging.ERROR)
        self.controller = self.app.controllers["PackageController"]

    def tearDown(self):
        self.app.unload()
        appier.conf_r("PACKAGES_PATH")
        appier.conf_r("PACKAGES_KEY")
        shutil.rmtree(self.packages_path, ignore_errors=True)
        adapter = appier.get_adapter()
        adapter.drop_db()

    def _headers(self):
        # creates an admin account and returns the headers with its secret
        # key, so that the requests are authenticated, the test is skipped
        # in case the accounts can't be created by the current adapter (eg:
        # the tiny adapter without tinydb installed)
        try:
            import appier_extras

            account = appier_extras.admin.Account(
                username="admin",
                email="admin@colony-print.com",
                password="password",
                password_confirm="password",
                type=appier_extras.admin.Account.ADMIN_TYPE,
            )
            account.save()
        except Exception as exception:
            self.skipTest("Accounts not available: %s" % str(exception))
        return [("X-Secret-Key", account.key)]

    def _publish_headers(self):
        return self._headers() + [("X-Packages-Key", PACKAGES_KEY)]

    def _upload(self, files, headers=[]):
        # builds the multipart request with the provided files, as sent
        # by a browser (or curl), notice that the content type header is
        # named so that the mock request sets it in the environment
        lines = []
        for name, data in files:
            lines.append(appier.legacy.bytes("--%s" % BOUNDARY))
            lines.append(
                appier.legacy.bytes(
                    'Content-Disposition: form-data; name="file"; filename="%s"' % name
                )
            )
            lines.append(b"Content-Type: application/octet-stream")
            lines.append(b"")
            lines.append(data)
        lines.append(appier.legacy.bytes("--%s--" % BOUNDARY))
        lines.append(b"")
        return self.app.post(
            "/packages",
            data=b"\r\n".join(lines),
            headers=headers
            + [("Content_Type", "multipart/form-data; boundary=%s" % BOUNDARY)],
        )

    def _write(self, name, data):
        with open(os.path.join(self.packages_path, name), "wb") as file:
            file.write(data)

    def _read(self, name):
        with open(os.path.join(self.packages_path, name), "rb") as file:
            return file.read()

    def _json(self, response):
        return json.loads(response.data.decode("utf-8"))

    def test_list(self):
        response = self.app.get("/packages")
        self.assertEqual(response.code, 403)

    def test_list_authorized(self):
        headers = self._headers()

        response = self.app.get("/packages", headers=headers)
        self.assertEqual(response.code, 200)
        self.assertEqual(self._json(response), [])

        self._write(WHEEL_NAME, b"wheel")
        self._write("notes.txt", b"notes")
        response = self.app.get("/packages", headers=headers)
        self.assertEqual(response.code, 200)
        packages = self._json(response)
        self.assertEqual(len(packages), 1)
        self.assertEqual(packages[0]["name"], "colony-print")
        self.assertEqual(packages[0]["version"], "0.21.0")
        self.assertEqual(packages[0]["file"], WHEEL_NAME)
        self.assertEqual(packages[0]["size"], 5)
        self.assertEqual(packages[0]["sha256"], hashlib.sha256(b"wheel").hexdigest())

    def test_list_o(self):
        response = self.app.options("/packages")
        self.assertEqual(response.code, 200)
        self.assertEqual(
            response.headers["Access-Control-Allow-Origin"].startswith("*"), True
        )
        self.assertEqual(
            response.headers["Access-Control-Allow-Headers"].startswith("*"), True
        )

    def test_upload(self):
        response = self._upload([(WHEEL_NAME, b"wheel")])
        self.assertEqual(response.code, 403)
        self.assertEqual(os.listdir(self.packages_path), [])

    def test_upload_authorized(self):
        headers = self._publish_headers()

        response = self._upload(
            [(WHEEL_NAME, b"wheel"), (NATIVE_NAME, b"native")], headers=headers
        )
        self.assertEqual(response.code, 200)
        packages = self._json(response)
        self.assertEqual(
            [(package["name"], package["version"]) for package in packages],
            [("colony-print", "0.21.0"), ("npcolony", "1.3.0")],
        )
        self.assertEqual(self._read(WHEEL_NAME), b"wheel")
        self.assertEqual(self._read(NATIVE_NAME), b"native")

        response = self._upload([(WHEEL_NAME, b"other wheel")], headers=headers)
        self.assertEqual(response.code, 200)
        self.assertEqual(self._read(WHEEL_NAME), b"other wheel")
        self.assertEqual(
            self._json(response)[0]["sha256"],
            hashlib.sha256(b"other wheel").hexdigest(),
        )

    def test_upload_invalid(self):
        headers = self._publish_headers()

        response = self._upload([], headers=headers)
        self.assertEqual(response.code, 400)

        response = self._upload([("notes.txt", b"notes")], headers=headers)
        self.assertEqual(response.code, 400)

        response = self._upload([("../" + WHEEL_NAME, b"wheel")], headers=headers)
        self.assertEqual(response.code, 400)

        response = self._upload([(WHEEL_NAME, b"")], headers=headers)
        self.assertEqual(response.code, 400)

        # the files are all validated before storing any of them, so that
        # no package is stored by a failed upload
        response = self._upload(
            [(WHEEL_NAME, b"wheel"), ("notes.txt", b"notes")], headers=headers
        )
        self.assertEqual(response.code, 400)

        response = self.app.post(
            "/packages",
            data=b"file=" + appier.legacy.bytes(WHEEL_NAME),
            headers=headers + [("Content_Type", "application/x-www-form-urlencoded")],
        )
        self.assertEqual(response.code, 400)
        self.assertEqual(os.listdir(self.packages_path), [])

    def test_show(self):
        self._write(WHEEL_NAME, b"wheel")
        response = self.app.get("/packages/%s" % WHEEL_NAME)
        self.assertEqual(response.code, 403)

    def test_show_authorized(self):
        headers = self._headers()

        self._write(WHEEL_NAME, b"wheel")
        response = self.app.get("/packages/%s" % WHEEL_NAME, headers=headers)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.data, b"wheel")

        response = self.app.get("/packages/%s" % NATIVE_NAME, headers=headers)
        self.assertEqual(response.code, 404)

        os.makedirs(os.path.join(self.packages_path, NATIVE_NAME))
        response = self.app.get("/packages/%s" % NATIVE_NAME, headers=headers)
        self.assertEqual(response.code, 404)

        self._write("notes.txt", b"notes")
        response = self.app.get("/packages/notes.txt", headers=headers)
        self.assertEqual(response.code, 400)

    def test_show_o(self):
        response = self.app.options("/packages/%s" % WHEEL_NAME)
        self.assertEqual(response.code, 200)
        self.assertEqual(
            response.headers["Access-Control-Allow-Origin"].startswith("*"), True
        )
        self.assertEqual(
            response.headers["Access-Control-Allow-Headers"].startswith("*"), True
        )

    def test_update(self):
        response = self.app.put("/packages/%s" % WHEEL_NAME, data=b"wheel")
        self.assertEqual(response.code, 403)
        self.assertEqual(os.listdir(self.packages_path), [])

    def test_update_authorized(self):
        headers = self._publish_headers() + [
            ("Content_Type", "application/octet-stream")
        ]

        response = self.app.put(
            "/packages/%s" % WHEEL_NAME, data=b"wheel", headers=headers
        )
        self.assertEqual(response.code, 200)
        package = self._json(response)
        self.assertEqual(package["name"], "colony-print")
        self.assertEqual(package["version"], "0.21.0")
        self.assertEqual(package["sha256"], hashlib.sha256(b"wheel").hexdigest())

        response = self.app.put(
            "/packages/%s" % WHEEL_NAME, data=b"other wheel", headers=headers
        )
        self.assertEqual(response.code, 200)
        self.assertEqual(self._read(WHEEL_NAME), b"other wheel")

        response = self.app.put("/packages/%s" % WHEEL_NAME, headers=headers)
        self.assertEqual(response.code, 400)
        self.assertEqual(self._read(WHEEL_NAME), b"other wheel")

        response = self.app.put("/packages/notes.txt", data=b"notes", headers=headers)
        self.assertEqual(response.code, 400)

        # a name with a line break is not a valid package name, even if it
        # ends with the name of a wheel (that the route accepts)
        response = self.app.put(
            "/packages/%s\n" % WHEEL_NAME, data=b"wheel", headers=headers
        )
        self.assertEqual(response.code, 400)
        self.assertEqual(os.listdir(self.packages_path), [WHEEL_NAME])

    def test_delete(self):
        self._write(WHEEL_NAME, b"wheel")
        response = self.app.delete("/packages/%s" % WHEEL_NAME)
        self.assertEqual(response.code, 403)
        self.assertEqual(os.listdir(self.packages_path), [WHEEL_NAME])

    def test_delete_authorized(self):
        headers = self._publish_headers()

        self._write(WHEEL_NAME, b"wheel")
        self.assertEqual(
            self.controller.digest(WHEEL_NAME), hashlib.sha256(b"wheel").hexdigest()
        )
        response = self.app.delete("/packages/%s" % WHEEL_NAME, headers=headers)
        self.assertEqual(response.code, 200)
        self.assertEqual(os.listdir(self.packages_path), [])
        self.assertEqual(self.controller.digests, dict())

        response = self.app.delete("/packages/%s" % WHEEL_NAME, headers=headers)
        self.assertEqual(response.code, 404)

        response = self.app.delete("/packages/notes.txt", headers=headers)
        self.assertEqual(response.code, 400)

    def test_packages(self):
        shutil.rmtree(self.packages_path)
        self.assertEqual(self.controller.packages(), [])

        os.makedirs(self.packages_path)
        self._write(WHEEL_NAME, b"wheel")
        self._write(NATIVE_NAME, b"native")
        self._write("Gravo.Pilot-1.0.0_rc1-py3-none-any.whl", b"gravo")
        self._write("notes.txt", b"notes")
        self._write(WHEEL_NAME + ".tmp", b"partial")
        os.makedirs(os.path.join(self.packages_path, "appier-1.40.0-py3-none-any.whl"))

        packages = self.controller.packages()
        self.assertEqual(
            [(package["name"], package["version"]) for package in packages],
            [
                ("gravo-pilot", "1.0.0-rc1"),
                ("colony-print", "0.21.0"),
                ("npcolony", "1.3.0"),
            ],
        )

    def test_store(self):
        shutil.rmtree(self.packages_path)

        package = self.controller.store(WHEEL_NAME, b"wheel")
        self.assertEqual(package["name"], "colony-print")
        self.assertEqual(package["sha256"], hashlib.sha256(b"wheel").hexdigest())
        self.assertEqual(os.listdir(self.packages_path), [WHEEL_NAME])

        package = self.controller.store(WHEEL_NAME, b"other wheel")
        self.assertEqual(package["size"], 11)
        self.assertEqual(package["sha256"], hashlib.sha256(b"other wheel").hexdigest())
        self.assertEqual(os.listdir(self.packages_path), [WHEEL_NAME])
        self.assertEqual(self._read(WHEEL_NAME), b"other wheel")

    def test_package_info(self):
        self._write(NATIVE_NAME, b"native")
        package = self.controller.package_info(NATIVE_NAME)
        self.assertEqual(package["name"], "npcolony")
        self.assertEqual(package["version"], "1.3.0")
        self.assertEqual(package["file"], NATIVE_NAME)
        self.assertEqual(package["size"], 6)
        self.assertEqual(
            package["modified"],
            os.path.getmtime(os.path.join(self.packages_path, NATIVE_NAME)),
        )
        self.assertEqual(package["sha256"], hashlib.sha256(b"native").hexdigest())

        self._write("notes.txt", b"notes")
        self.assertEqual(self.controller.package_info(WHEEL_NAME), None)
        self.assertEqual(self.controller.package_info("notes.txt"), None)
        self.assertEqual(self.controller.package_info("../" + NATIVE_NAME), None)

    def test_digest(self):
        self._write(WHEEL_NAME, b"wheel")
        self.assertEqual(
            self.controller.digest(WHEEL_NAME), hashlib.sha256(b"wheel").hexdigest()
        )
        self.assertEqual(list(self.controller.digests.keys()), [WHEEL_NAME])

        # the digest is kept while the size and the modification time of
        # the package are the same, so it's not calculated on every listing,
        # notice that the modification time is set in whole seconds so that
        # it's kept exactly (Python 2 sets it with microseconds precision)
        file_path = os.path.join(self.packages_path, WHEEL_NAME)
        os.utime(file_path, (1700000000, 1700000000))
        self.assertEqual(
            self.controller.digest(WHEEL_NAME), hashlib.sha256(b"wheel").hexdigest()
        )
        self._write(WHEEL_NAME, b"WHEEL")
        os.utime(file_path, (1700000000, 1700000000))
        self.assertEqual(
            self.controller.digest(WHEEL_NAME), hashlib.sha256(b"wheel").hexdigest()
        )

        data = b"wheel" * colony_print.controllers.package.CHUNK_SIZE
        self._write(WHEEL_NAME, data)
        self.assertEqual(
            self.controller.digest(WHEEL_NAME), hashlib.sha256(data).hexdigest()
        )

    def test_verify_name(self):
        self.controller.verify_name(WHEEL_NAME)
        self.controller.verify_name(NATIVE_NAME)
        self.controller.verify_name("npcolony-1.3.0-1-cp313-cp313-win_amd64.whl")
        for name in (
            "notes.txt",
            "colony_print-0.21.0.tar.gz",
            "../" + WHEEL_NAME,
            "..\\" + WHEEL_NAME,
            "dir/" + WHEEL_NAME,
            WHEEL_NAME + "\n",
            "",
            None,
        ):
            self.assertRaises(
                appier.AppierException, lambda: self.controller.verify_name(name)
            )

    def test_verify_publish(self):
        headers = self._headers()
        put_headers = [("Content_Type", "application/octet-stream")]
        self._write(WHEEL_NAME, b"wheel")

        # the secret key (kept by the nodes) alone is not able to publish
        # packages, neither with an invalid packages key, while it's still
        # able to list and download them
        for key in (None, "invalid", PACKAGES_KEY[:-1], PACKAGES_KEY + "\u00e9"):
            key_headers = headers + ([("X-Packages-Key", key)] if key else [])
            response = self._upload([(NATIVE_NAME, b"native")], headers=key_headers)
            self.assertEqual(response.code, 403)
            response = self.app.put(
                "/packages/%s" % NATIVE_NAME,
                data=b"native",
                headers=key_headers + put_headers,
            )
            self.assertEqual(response.code, 403)
            response = self.app.delete("/packages/%s" % WHEEL_NAME, headers=key_headers)
            self.assertEqual(response.code, 403)
        self.assertEqual(os.listdir(self.packages_path), [WHEEL_NAME])

        response = self.app.get("/packages", headers=headers)
        self.assertEqual(response.code, 200)
        response = self.app.get("/packages/%s" % WHEEL_NAME, headers=headers)
        self.assertEqual(response.code, 200)

        # without a packages key defined the publishing is disabled, even
        # for the requests that send the (previous) packages key
        appier.conf_r("PACKAGES_KEY")
        headers += [("X-Packages-Key", PACKAGES_KEY)]
        response = self._upload([(NATIVE_NAME, b"native")], headers=headers)
        self.assertEqual(response.code, 403)
        response = self.app.delete("/packages/%s" % WHEEL_NAME, headers=headers)
        self.assertEqual(response.code, 403)
        self.assertEqual(os.listdir(self.packages_path), [WHEEL_NAME])

    def test_normalize(self):
        self.assertEqual(self.controller.normalize("colony_print"), "colony-print")
        self.assertEqual(self.controller.normalize("Gravo.Pilot"), "gravo-pilot")
        self.assertEqual(self.controller.normalize("mailme__api"), "mailme-api")

    def test_packages_path(self):
        self.assertEqual(self.controller.packages_path, self.packages_path)

        data_path = appier.conf("DATA_PATH", None)
        appier.conf_r("PACKAGES_PATH")
        appier.conf_s("DATA_PATH", "/var/colony-print")
        try:
            self.assertEqual(
                self.controller.packages_path,
                os.path.join("/var/colony-print", "packages"),
            )
        finally:
            if data_path == None:
                appier.conf_r("DATA_PATH")
            else:
                appier.conf_s("DATA_PATH", data_path)
