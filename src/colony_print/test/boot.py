#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import json
import codecs
import shutil
import hashlib
import tempfile
import unittest

import colony_print.boot


class MockResponse(object):
    def __init__(self, data):
        self.data = data
        self.offset = 0

    def read(self, size=-1):
        if size < 0:
            size = len(self.data) - self.offset
        data = self.data[self.offset : self.offset + size]
        self.offset += len(data)
        return data

    def close(self):
        pass


class MockBoot(colony_print.boot.ColonyPrintBoot):
    def __init__(self, files=None, installed=None, environ=None):
        colony_print.boot.ColonyPrintBoot.__init__(
            self, environ=dict() if environ == None else environ, retry_delay=0.0
        )
        self.files = files or dict()
        self.installed = installed or dict()
        self.urls = []
        self.installs = []

    def open(self, url, timeout=colony_print.boot.TIMEOUT):
        self.urls.append(url)
        if url == self.packages_url:
            return MockResponse(json.dumps(self.packages()).encode("utf-8"))
        name = url[len(self.packages_url) + 1 :]
        return MockResponse(self.files[name])

    def packages(self):
        return [
            dict(file=name, sha256=hashlib.sha256(data).hexdigest())
            for name, data in sorted(self.files.items())
        ]

    def install(self, packages_path, requirements):
        self.installs.append((packages_path, requirements))

    def installed_version(self, name):
        return self.installed.get(name, None)

    @property
    def tags(self):
        return (
            set(["py3", "py314", "cp314"]),
            set(["none", "abi3", "cp314"]),
            set(["any", "win_amd64"]),
        )


class BootTest(unittest.TestCase):
    def setUp(self):
        self.temp_path = tempfile.mkdtemp()
        self.packages_path = os.path.join(self.temp_path, "packages")

    def tearDown(self):
        shutil.rmtree(self.temp_path, ignore_errors=True)

    def test_version_key(self):
        boot = colony_print.boot.ColonyPrintBoot(environ=dict())
        versions = [
            "invalid",
            "0.9",
            "1.0.0.dev1",
            "1.0.0a1",
            "1.0.0b2",
            "1.0.0rc1",
            "1.0.0",
            "1.0.0.post1",
            "1.0.1",
            "1.2",
            "1.10",
            "2!0.1",
        ]
        keys = [boot.version_key(version) for version in versions]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(len(set(keys)), len(keys))
        self.assertEqual(boot.version_key("1.0"), boot.version_key("1.0.0"))
        self.assertEqual(boot.version_key("1.0.0-rc1"), boot.version_key("1.0.0rc1"))
        self.assertEqual(boot.version_key("v1.0"), boot.version_key("1.0"))

    def test_normalize(self):
        boot = colony_print.boot.ColonyPrintBoot(environ=dict())
        self.assertEqual(boot.normalize("colony_print"), "colony-print")
        self.assertEqual(boot.normalize("Gravo.Pilot"), "gravo-pilot")
        self.assertEqual(boot.normalize("mailme__api"), "mailme-api")

    def test_compatible(self):
        boot = MockBoot()
        self.assertEqual(
            boot.compatible(dict(file="colony_print-0.21.0-py2.py3-none-any.whl")), True
        )
        self.assertEqual(
            boot.compatible(dict(file="npcolony-1.3.0-cp314-cp314-win_amd64.whl")),
            True,
        )
        self.assertEqual(
            boot.compatible(dict(file="npcolony-1.3.0-cp313-cp313-win_amd64.whl")),
            False,
        )
        self.assertEqual(
            boot.compatible(dict(file="npcolony-1.3.0-cp314-cp314-win32.whl")),
            False,
        )
        self.assertEqual(
            boot.compatible(
                dict(file="pillow-11.0.0-cp314-cp314-manylinux_2_28_x86_64.whl")
            ),
            False,
        )
        self.assertEqual(boot.compatible(dict(file="colony_print-0.21.0.zip")), False)
        self.assertEqual(boot.compatible(dict()), False)

    def test_tags(self):
        boot = colony_print.boot.ColonyPrintBoot(environ=dict())
        pythons, abis, platforms = boot.tags
        major, minor = sys.version_info[0], sys.version_info[1]
        self.assertEqual("py%d" % major in pythons, True)
        self.assertEqual("cp%d%d" % (major, minor) in abis, True)
        self.assertEqual("any" in platforms, True)

    def test_select(self):
        boot = MockBoot()
        versions = boot.select(
            [
                dict(file="colony_print-0.21.0-py2.py3-none-any.whl"),
                dict(file="colony_print-0.20.0-py2.py3-none-any.whl"),
                dict(file="colony_print-0.21.0rc1-py2.py3-none-any.whl"),
                dict(file="npcolony-1.3.0-cp314-cp314-win_amd64.whl"),
                dict(file="npcolony-1.10.0-cp314-cp314-win_amd64.whl"),
                dict(file="npcolony-1.9.0-cp314-cp314-win_amd64.whl"),
            ]
        )
        self.assertEqual(versions, {"colony-print": "0.21.0", "npcolony": "1.10.0"})

    def test_outdated(self):
        boot = MockBoot(
            installed={
                "colony-print": "0.21.0",
                "pillow": "11.0.0",
                "appier": "1.40.0",
            }
        )
        requirements = boot.outdated(
            {
                "colony-print": "0.21",
                "npcolony": "1.3.0",
                "pillow": "10.4.0",
                "appier": "1.41.0",
                "gravo-pilot": "1.0.0",
            }
        )
        self.assertEqual(
            requirements,
            [("appier", "1.41.0"), ("npcolony", "1.3.0"), ("pillow", "10.4.0")],
        )

    def test_update(self):
        files = {
            "colony_print-0.21.0-py2.py3-none-any.whl": b"colony-print",
            "npcolony-1.3.0-cp314-cp314-win_amd64.whl": b"npcolony",
            "npcolony-1.3.0-cp313-cp313-win_amd64.whl": b"npcolony-313",
            "appier-1.40.0-py2.py3-none-any.whl": b"appier",
        }
        boot = MockBoot(
            files=files,
            installed={"colony-print": "0.20.0", "npcolony": "1.3.0", "appier": "1.40"},
            environ=dict(BASE_URL="https://print.example.com"),
        )

        os.makedirs(self.packages_path)
        stale_path = os.path.join(self.packages_path, "appier-1.39.0-py3-none-any.whl")
        with open(stale_path, "wb") as file:
            file.write(b"stale")
        other_path = os.path.join(self.packages_path, "notes.txt")
        with open(other_path, "wb") as file:
            file.write(b"notes")

        requirements = boot.update(self.packages_path)
        self.assertEqual(requirements, [("colony-print", "0.21.0")])
        self.assertEqual(
            boot.installs, [(self.packages_path, [("colony-print", "0.21.0")])]
        )
        self.assertEqual(
            sorted(os.listdir(self.packages_path)),
            [
                "appier-1.40.0-py2.py3-none-any.whl",
                "colony_print-0.21.0-py2.py3-none-any.whl",
                "notes.txt",
                "npcolony-1.3.0-cp314-cp314-win_amd64.whl",
            ],
        )
        with open(
            os.path.join(
                self.packages_path, "colony_print-0.21.0-py2.py3-none-any.whl"
            ),
            "rb",
        ) as file:
            self.assertEqual(file.read(), b"colony-print")
        self.assertEqual(boot.urls[0], "https://print.example.com/packages")
        self.assertEqual(len(boot.urls), 4)

        # runs the update once more, which should neither download
        # any package (already mirrored) nor install any of them as
        # they are considered to be installed
        boot.urls = []
        boot.installs = []
        boot.installed["colony-print"] = "0.21.0"
        requirements = boot.update(self.packages_path)
        self.assertEqual(requirements, [])
        self.assertEqual(boot.installs, [])
        self.assertEqual(boot.urls, ["https://print.example.com/packages"])

    def test_download_digest(self):
        boot = MockBoot(files={"appier-1.40.0-py3-none-any.whl": b"appier"})
        os.makedirs(self.packages_path)
        file_path = os.path.join(self.packages_path, "appier-1.40.0-py3-none-any.whl")
        self.assertRaises(
            ValueError,
            lambda: boot.download(
                "appier-1.40.0-py3-none-any.whl", file_path, sha256="invalid"
            ),
        )
        self.assertEqual(os.listdir(self.packages_path), [])

        boot.download(
            "appier-1.40.0-py3-none-any.whl",
            file_path,
            sha256=hashlib.sha256(b"appier").hexdigest(),
        )
        self.assertEqual(
            os.listdir(self.packages_path), ["appier-1.40.0-py3-none-any.whl"]
        )

    def test_fetch_packages(self):
        boot = MockBoot()
        boot.packages = lambda: [
            dict(file="appier-1.40.0-py3-none-any.whl"),
            dict(file="../appier-1.40.0-py3-none-any.whl"),
            dict(file="appier.txt"),
            dict(name="appier"),
            "appier",
        ]
        self.assertEqual(
            boot.fetch_packages(), [dict(file="appier-1.40.0-py3-none-any.whl")]
        )

        boot.packages = lambda: dict(result="success")
        self.assertRaises(ValueError, boot.fetch_packages)

    def test_fetch_packages_retry(self):
        boot = MockBoot()
        failures = []

        def request(url, timeout=None):
            if len(failures) < 2:
                failures.append(url)
                raise IOError("Network unreachable")
            return b"[]"

        boot.request = request
        self.assertEqual(boot.fetch_packages(), [])
        self.assertEqual(len(failures), 2)

        failures = []
        boot.retries = 2
        self.assertRaises(IOError, boot.fetch_packages)
        self.assertEqual(len(failures), 2)

        class HTTPError(IOError):
            code = 404

        def request_http(url, timeout=None):
            failures.append(url)
            raise HTTPError("Not Found")

        failures = []
        boot.request = request_http
        self.assertRaises(HTTPError, boot.fetch_packages)
        self.assertEqual(len(failures), 1)

    def test_load_config(self):
        boot = colony_print.boot.ColonyPrintBoot(environ=dict())
        config_path = os.path.join(self.temp_path, "config.env")
        self.assertEqual(boot.load_config(config_path), dict())

        with open(config_path, "wb") as file:
            file.write(codecs.BOM_UTF8)
            file.write(
                b"# Colony Print node\r\n"
                b"BASE_URL=https://print.example.com/\r\n"
                b"SECRET_KEY = secret=key \r\n"
                b'NODE_NAME="Shop Node"\r\n'
                b"NODE_LOCATION='Porto'\r\n"
                b"\r\n"
                b"INVALID\r\n"
                b"NODE_EMAIL_RECEIVERS=a@example.com;b@example.com\r\n"
            )
        self.assertEqual(
            boot.load_config(config_path),
            dict(
                BASE_URL="https://print.example.com/",
                SECRET_KEY="secret=key",
                NODE_NAME="Shop Node",
                NODE_LOCATION="Porto",
                NODE_EMAIL_RECEIVERS="a@example.com;b@example.com",
            ),
        )

    def test_apply_config(self):
        environ = dict(BASE_URL="https://other.example.com/")
        boot = colony_print.boot.ColonyPrintBoot(environ=environ)
        boot.apply_config(
            dict(BASE_URL="https://print.example.com/", SECRET_KEY="secret")
        )
        self.assertEqual(
            environ,
            dict(BASE_URL="https://other.example.com/", SECRET_KEY="secret"),
        )

    def test_urls(self):
        boot = colony_print.boot.ColonyPrintBoot(environ=dict())
        self.assertEqual(boot.base_url, colony_print.boot.BASE_URL)
        self.assertEqual(boot.packages_url, colony_print.boot.BASE_URL + "packages")

        boot = colony_print.boot.ColonyPrintBoot(
            environ=dict(BASE_URL="http://localhost:8080")
        )
        self.assertEqual(boot.base_url, "http://localhost:8080/")
        self.assertEqual(boot.packages_url, "http://localhost:8080/packages")

        boot = colony_print.boot.ColonyPrintBoot(
            environ=dict(PACKAGES_URL="http://localhost:9090/repo/")
        )
        self.assertEqual(boot.packages_url, "http://localhost:9090/repo")

    def test_update_enabled(self):
        boot = colony_print.boot.ColonyPrintBoot(environ=dict())
        self.assertEqual(boot.update_enabled, True)
        for value in ("0", "false", "False", "no", " off "):
            boot = colony_print.boot.ColonyPrintBoot(environ=dict(NODE_UPDATE=value))
            self.assertEqual(boot.update_enabled, False)
        boot = colony_print.boot.ColonyPrintBoot(environ=dict(NODE_UPDATE="1"))
        self.assertEqual(boot.update_enabled, True)

    def test_main(self):
        config_path = os.path.join(self.temp_path, "config.env")
        with open(config_path, "wb") as file:
            file.write(b"BASE_URL=https://print.example.com\r\nSECRET_KEY=secret\r\n")

        environ = dict()
        boot = MockBoot(
            files={"colony_print-0.21.0-py2.py3-none-any.whl": b"colony-print"},
            environ=environ,
        )
        boot.main(["--config", config_path, "--update-only"])
        self.assertEqual(environ["BASE_URL"], "https://print.example.com/")
        self.assertEqual(environ["SECRET_KEY"], "secret")
        self.assertEqual(
            boot.installs, [(self.packages_path, [("colony-print", "0.21.0")])]
        )

        # makes sure that a failed update does not prevent the node from
        # running, as the installed packages keep being used
        runs = []
        boot = MockBoot(environ=dict(BASE_URL="https://print.example.com/"))
        boot.files = None
        boot.run = lambda: runs.append(True)
        boot.main(["--config", config_path])
        self.assertEqual(runs, [True])

        runs = []
        boot = MockBoot(environ=dict())
        boot.run = lambda: runs.append(True)
        boot.main(["--config", config_path, "--no-update"])
        self.assertEqual(boot.urls, [])
        self.assertEqual(runs, [True])
