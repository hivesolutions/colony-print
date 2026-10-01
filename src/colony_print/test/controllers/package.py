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

BOUNDARY = "colony-print-boundary"
""" The boundary used in the multipart requests of the tests """


class PackageControllerTest(unittest.TestCase):
    def setUp(self):
        self.packages_path = tempfile.mkdtemp()
        appier.conf_s("PACKAGES_PATH", self.packages_path)
        self.app = colony_print.ColonyPrintApp(level=logging.ERROR)
        self.controller = self.app.controllers["PackageController"]

    def tearDown(self):
        self.app.unload()
        appier.conf_r("PACKAGES_PATH")
        shutil.rmtree(self.packages_path, ignore_errors=True)
        adapter = appier.get_adapter()
        adapter.drop_db()

    def _secret_key(self):
        # creates an admin account and returns its secret key so that the
        # requests are authenticated, the test is skipped in case accounts
        # can't be created by the current adapter (eg: missing tinydb)
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
        return account.key

    def _multipart(self, files):
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
        return b"\r\n".join(lines)

    def test_list(self):
        response = self.app.get("/packages")
        self.assertEqual(response.code, 403)

    def test_list_o(self):
        response = self.app.options("/packages")
        self.assertEqual(response.code, 200)
        self.assertEqual(
            response.headers["Access-Control-Allow-Origin"].startswith("*"), True
        )

    def test_upload(self):
        response = self.app.post("/packages")
        self.assertEqual(response.code, 403)

    def test_show(self):
        response = self.app.get("/packages/%s" % WHEEL_NAME)
        self.assertEqual(response.code, 403)

    def test_show_o(self):
        response = self.app.options("/packages/%s" % WHEEL_NAME)
        self.assertEqual(response.code, 200)

    def test_update(self):
        response = self.app.put("/packages/%s" % WHEEL_NAME, data=b"wheel")
        self.assertEqual(response.code, 403)
        self.assertEqual(os.listdir(self.packages_path), [])

    def test_delete(self):
        response = self.app.delete("/packages/%s" % WHEEL_NAME)
        self.assertEqual(response.code, 403)

    def test_packages(self):
        self.assertEqual(self.controller.packages(), [])

        self.controller.store(WHEEL_NAME, b"wheel")
        self.controller.store("npcolony-1.3.0-cp313-cp313-win_amd64.whl", b"native")
        self.controller.store("Gravo.Pilot-1.0.0_rc1-py3-none-any.whl", b"gravo")
        with open(os.path.join(self.packages_path, "notes.txt"), "wb") as file:
            file.write(b"notes")
        with open(os.path.join(self.packages_path, WHEEL_NAME + ".tmp"), "wb") as file:
            file.write(b"partial")

        packages = self.controller.packages()
        self.assertEqual(len(packages), 3)
        self.assertEqual(
            [(package["name"], package["version"]) for package in packages],
            [
                ("gravo-pilot", "1.0.0-rc1"),
                ("colony-print", "0.21.0"),
                ("npcolony", "1.3.0"),
            ],
        )
        self.assertEqual(packages[1]["file"], WHEEL_NAME)
        self.assertEqual(packages[1]["size"], 5)
        self.assertEqual(packages[1]["sha256"], hashlib.sha256(b"wheel").hexdigest())

    def test_store(self):
        package = self.controller.store(WHEEL_NAME, b"wheel")
        self.assertEqual(package["name"], "colony-print")
        self.assertEqual(package["version"], "0.21.0")
        self.assertEqual(package["sha256"], hashlib.sha256(b"wheel").hexdigest())

        package = self.controller.store(WHEEL_NAME, b"other wheel")
        self.assertEqual(package["size"], 11)
        self.assertEqual(package["sha256"], hashlib.sha256(b"other wheel").hexdigest())
        self.assertEqual(os.listdir(self.packages_path), [WHEEL_NAME])

    def test_package_info(self):
        self.assertEqual(self.controller.package_info(WHEEL_NAME), None)
        self.assertEqual(self.controller.package_info("notes.txt"), None)
        self.assertEqual(self.controller.package_info("../" + WHEEL_NAME), None)

    def test_verify_name(self):
        self.controller.verify_name(WHEEL_NAME)
        self.controller.verify_name("npcolony-1.3.0-1-cp313-cp313-win_amd64.whl")
        self.assertRaises(
            appier.AppierException, lambda: self.controller.verify_name("notes.txt")
        )
        self.assertRaises(
            appier.AppierException,
            lambda: self.controller.verify_name("../" + WHEEL_NAME),
        )
        self.assertRaises(
            appier.AppierException,
            lambda: self.controller.verify_name("..\\" + WHEEL_NAME),
        )
        self.assertRaises(
            appier.AppierException, lambda: self.controller.verify_name(None)
        )

    def test_authenticated(self):
        headers = [("X-Secret-Key", self._secret_key())]

        response = self.app.get("/packages", headers=headers)
        self.assertEqual(response.code, 200)
        self.assertEqual(json.loads(response.data.decode("utf-8")), [])

        response = self.app.put(
            "/packages/%s" % WHEEL_NAME, data=b"wheel", headers=headers
        )
        self.assertEqual(response.code, 200)
        package = json.loads(response.data.decode("utf-8"))
        self.assertEqual(package["name"], "colony-print")
        self.assertEqual(package["version"], "0.21.0")

        response = self.app.put("/packages/notes.txt", data=b"notes", headers=headers)
        self.assertEqual(response.code, 400)

        response = self.app.put("/packages/%s" % WHEEL_NAME, headers=headers)
        self.assertEqual(response.code, 400)

        data = self._multipart(
            [
                ("npcolony-1.3.0-cp313-cp313-win_amd64.whl", b"native"),
                ("mailme_api-0.2.2-py2.py3-none-any.whl", b"mailme"),
            ]
        )
        response = self.app.post(
            "/packages",
            data=data,
            headers=headers
            + [("Content_Type", "multipart/form-data; boundary=%s" % BOUNDARY)],
        )
        self.assertEqual(response.code, 200)
        packages = json.loads(response.data.decode("utf-8"))
        self.assertEqual(
            [package["name"] for package in packages], ["npcolony", "mailme-api"]
        )

        data = self._multipart([("notes.txt", b"notes")])
        response = self.app.post(
            "/packages",
            data=data,
            headers=headers
            + [("Content_Type", "multipart/form-data; boundary=%s" % BOUNDARY)],
        )
        self.assertEqual(response.code, 400)

        response = self.app.get("/packages", headers=headers)
        self.assertEqual(response.code, 200)
        packages = json.loads(response.data.decode("utf-8"))
        self.assertEqual(len(packages), 3)

        response = self.app.get("/packages/%s" % WHEEL_NAME, headers=headers)
        self.assertEqual(response.code, 200)
        self.assertEqual(response.data, b"wheel")

        response = self.app.get(
            "/packages/colony_print-0.1.0-py3-none-any.whl", headers=headers
        )
        self.assertEqual(response.code, 404)

        response = self.app.delete("/packages/%s" % WHEEL_NAME, headers=headers)
        self.assertEqual(response.code, 200)
        self.assertEqual(
            os.path.exists(os.path.join(self.packages_path, WHEEL_NAME)), False
        )

        response = self.app.delete("/packages/%s" % WHEEL_NAME, headers=headers)
        self.assertEqual(response.code, 404)
