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

import appier

import colony_print.boot
import colony_print.node

WHEEL_NAME = "colony_print-0.21.0-py2.py3-none-any.whl"
""" The (file) name of the wheel package of colony print, the
one updated by the boot in most of the tests """

APPIER_NAME = "appier-1.40.0-py2.py3-none-any.whl"
""" The (file) name of the wheel package of appier, a dependency
of colony print that is also hosted by the server """


class MockResponse(object):
    """
    Stand-in for the response of urllib that serves the provided data
    in chunks, keeping track of its closing, so that the responses are
    verified to be closed once read.
    """

    def __init__(self, data):
        self.data = data
        self.offset = 0
        self.closed = False

    def read(self, size=-1):
        if size < 0:
            size = len(self.data) - self.offset
        data = self.data[self.offset : self.offset + size]
        self.offset += len(data)
        return data

    def close(self):
        self.closed = True


class MockBrokenResponse(MockResponse):
    """
    Stand-in for a response of urllib whose connection is lost after
    the first chunk of data (eg: a timeout or a connection reset).
    """

    def read(self, size=-1):
        if self.offset > 0:
            raise IOError("Connection reset")
        return MockResponse.read(self, size)


class MockOpener(object):
    """
    Stand-in for the opener of urllib, that opens the requests through
    the stand-in of the urllib request module.
    """

    def open(self, request, timeout=None):
        return MockUrllibRequest.urlopen(request, timeout=timeout)


class MockRequest(object):
    """
    Stand-in for the request class of urllib that keeps the URL and the
    headers of the request, so that they can be inspected by the tests.
    """

    def __init__(self, url, headers=None):
        self.url = url
        self.headers = headers or dict()


class MockHTTPError(IOError):
    """
    Stand-in for the HTTP error of urllib, an error returned by the server
    itself (with a status code), that is not retried by the boot.
    """

    code = 404


class MockUrllibRequest(object):
    """
    Stand-in for the urllib request module that serves the listing and
    the files of the packages of a (mock) server, recording the requests
    made to it and raising the queued errors, so that the update of the
    node can be exercised without a server.
    """

    Request = MockRequest
    files = dict()
    listing = None
    broken = False
    errors = []
    requests = []
    responses = []
    handlers = []

    @staticmethod
    def build_opener(*handlers):
        MockUrllibRequest.handlers.extend(handlers)
        return MockOpener()

    @staticmethod
    def urlopen(request, timeout=None):
        MockUrllibRequest.requests.append((request, timeout))
        if MockUrllibRequest.errors:
            raise MockUrllibRequest.errors.pop(0)
        if request.url.endswith("/packages"):
            listing = MockUrllibRequest.listing
            if listing == None:
                listing = [
                    dict(file=name, sha256=hashlib.sha256(data).hexdigest())
                    for name, data in sorted(MockUrllibRequest.files.items())
                ]
            data = json.dumps(listing).encode("utf-8")
        else:
            data = MockUrllibRequest.files[request.url.rsplit("/", 1)[1]]
        response_class = (
            MockBrokenResponse if MockUrllibRequest.broken else MockResponse
        )
        response = response_class(data)
        MockUrllibRequest.responses.append(response)
        return response


class MockSubprocess(object):
    """
    Stand-in for the subprocess module that records the commands that
    are called and returns a configurable exit code, so that the install
    of the packages can be exercised without pip.
    """

    code = 0
    calls = []

    @staticmethod
    def call(command):
        MockSubprocess.calls.append(command)
        return MockSubprocess.code


class MockColonyPrintNode(object):
    """
    Stand-in for the node that counts the loops run on it, so that the
    running of the node by the boot can be exercised without a server.
    """

    loops = 0

    def loop(self):
        MockColonyPrintNode.loops += 1


class SecretRedirectHandlerTest(unittest.TestCase):
    def test_redirect_request(self):
        boot = colony_print.boot.ColonyPrintBoot(environ=dict())
        handler = colony_print.boot.SecretRedirectHandler(boot)
        request = colony_print.boot.urllib_request.Request(
            "https://print.example.com/packages/" + WHEEL_NAME,
            headers={"User-Agent": colony_print.boot.NAME, "X-Secret-Key": "key"},
        )

        redirected = handler.redirect_request(
            request, None, 302, "Found", {}, "https://print.example.com/files"
        )
        self.assertEqual(redirected.get_header("X-secret-key"), "key")

        # the secret key never leaves the origin of the original request,
        # be it another host, another port or a downgrade to HTTP, while
        # the other headers are kept
        for url in (
            "https://cdn.example.com/files",
            "http://print.example.com/files",
            "https://print.example.com:8443/files",
        ):
            redirected = handler.redirect_request(request, None, 302, "Found", {}, url)
            self.assertEqual(redirected.get_header("X-secret-key"), None)
            self.assertEqual(
                redirected.get_header("User-agent"), colony_print.boot.NAME
            )


class ColonyPrintBootTest(unittest.TestCase):
    def setUp(self):
        self.environ = dict(BASE_URL="https://print.example.com/", SECRET_KEY="key")
        self.boot = colony_print.boot.ColonyPrintBoot(
            environ=self.environ, retry_delay=0.0
        )
        self.temp_path = tempfile.mkdtemp(prefix="colony-print-boot-test-")
        self.packages_path = os.path.join(self.temp_path, "packages")
        self.config_path = os.path.join(self.temp_path, "config.env")
        MockUrllibRequest.files = dict()
        MockUrllibRequest.listing = None
        MockUrllibRequest.broken = False
        MockUrllibRequest.errors = []
        MockUrllibRequest.requests = []
        MockUrllibRequest.responses = []
        MockUrllibRequest.handlers = []
        MockSubprocess.code = 0
        MockSubprocess.calls = []
        MockColonyPrintNode.loops = 0
        self._urllib_request = colony_print.boot.urllib_request
        colony_print.boot.urllib_request = MockUrllibRequest
        self._subprocess = colony_print.boot.subprocess
        colony_print.boot.subprocess = MockSubprocess
        self._node = colony_print.node.ColonyPrintNode
        colony_print.node.ColonyPrintNode = MockColonyPrintNode

    def tearDown(self):
        shutil.rmtree(self.temp_path, ignore_errors=True)
        colony_print.boot.urllib_request = self._urllib_request
        colony_print.boot.subprocess = self._subprocess
        colony_print.node.ColonyPrintNode = self._node

    def _installed(self, **kwargs):
        # makes the boot consider the provided (normalized) names as the
        # installed packages with the provided versions, as the packages
        # installed in the environment of the tests are not controlled
        installed = dict(
            (name.replace("_", "-"), value) for name, value in kwargs.items()
        )
        self.boot.installed_version = lambda name: installed.get(name, None)

    def _write(self, path, data):
        with open(path, "wb") as file:
            file.write(data)

    def _read(self, path):
        with open(path, "rb") as file:
            return file.read()

    def _urls(self):
        return [request.url for request, _timeout in MockUrllibRequest.requests]

    def _requirements(self):
        return [
            [argument for argument in command if "<=" in argument]
            for command in MockSubprocess.calls
        ]

    def test_main(self):
        self._write(
            self.config_path,
            b"BASE_URL=https://print.example.com\r\nSECRET_KEY=secret\r\n",
        )
        MockUrllibRequest.files[WHEEL_NAME] = b"colony-print"
        environ = dict()
        boot = colony_print.boot.ColonyPrintBoot(environ=environ, retry_delay=0.0)
        boot.installed_version = lambda name: None

        boot.main(["--config", self.config_path])
        self.assertEqual(environ["BASE_URL"], "https://print.example.com/")
        self.assertEqual(environ["SECRET_KEY"], "secret")
        self.assertEqual(
            self._urls(),
            [
                "https://print.example.com/packages",
                "https://print.example.com/packages/" + WHEEL_NAME,
            ],
        )
        self.assertEqual(
            os.path.exists(os.path.join(self.packages_path, WHEEL_NAME)), True
        )
        self.assertEqual(self._requirements(), [["colony-print<=0.21.0"]])
        self.assertEqual(MockColonyPrintNode.loops, 1)

    def test_main_config_default(self):
        self._write(self.config_path, b"NODE_UPDATE=0\r\nNODE_NAME=Shop\r\n")
        environ = dict(COLONY_PRINT_CONFIG=self.config_path)
        boot = colony_print.boot.ColonyPrintBoot(environ=environ, retry_delay=0.0)

        boot.main([])
        self.assertEqual(environ["NODE_NAME"], "Shop")
        self.assertEqual(environ["BASE_URL"], colony_print.boot.BASE_URL)
        self.assertEqual(MockUrllibRequest.requests, [])
        self.assertEqual(MockColonyPrintNode.loops, 1)

    def test_main_config_missing(self):
        self.boot.main(["--config", self.config_path, "--no-update"])
        self.assertEqual(self.environ["BASE_URL"], "https://print.example.com/")
        self.assertEqual(MockColonyPrintNode.loops, 1)

    def test_main_packages(self):
        MockUrllibRequest.files[WHEEL_NAME] = b"colony-print"
        self._installed(colony_print="0.20.0")
        packages_path = os.path.join(self.temp_path, "mirror")

        self.boot.main(
            [
                "--config",
                self.config_path,
                "--packages",
                packages_path,
                "--update-only",
            ]
        )
        self.assertEqual(os.listdir(packages_path), [WHEEL_NAME])
        self.assertEqual(os.path.exists(self.packages_path), False)
        command = MockSubprocess.calls[0]
        self.assertEqual(command[command.index("--find-links") + 1], packages_path)
        self.assertEqual(MockColonyPrintNode.loops, 0)

    def test_main_no_update(self):
        self.boot.main(["--config", self.config_path, "--no-update"])
        self.assertEqual(MockUrllibRequest.requests, [])
        self.assertEqual(MockSubprocess.calls, [])
        self.assertEqual(MockColonyPrintNode.loops, 1)

    def test_main_update_disabled(self):
        self._write(self.config_path, b"NODE_UPDATE=false\r\n")
        self.boot.main(["--config", self.config_path])
        self.assertEqual(MockUrllibRequest.requests, [])
        self.assertEqual(MockColonyPrintNode.loops, 1)

    def test_main_update_error(self):
        # makes sure that a failed update (the server returning an error
        # or the installation failing) never prevents the node from running
        MockUrllibRequest.errors = [MockHTTPError("Not Found")]
        self.boot.main(["--config", self.config_path])
        self.assertEqual(len(MockUrllibRequest.requests), 1)
        self.assertEqual(MockColonyPrintNode.loops, 1)

        MockUrllibRequest.files[WHEEL_NAME] = b"colony-print"
        MockSubprocess.code = 1
        self._installed(colony_print="0.20.0")
        self.boot.main(["--config", self.config_path])
        self.assertEqual(self._requirements(), [["colony-print<=0.21.0"]])
        self.assertEqual(MockColonyPrintNode.loops, 2)

    def test_run(self):
        self.boot.run()
        self.assertEqual(MockColonyPrintNode.loops, 1)

    def test_update(self):
        MockUrllibRequest.files[WHEEL_NAME] = b"colony-print"
        MockUrllibRequest.files[APPIER_NAME] = b"appier"
        MockUrllibRequest.files["npcolony-1.3.0-cp27-cp27m-win32.whl"] = b"npcolony"
        self._installed(colony_print="0.20.0", appier="1.40")

        requirements = self.boot.update(self.packages_path)
        self.assertEqual(requirements, [("colony-print", "0.21.0")])
        self.assertEqual(self._requirements(), [["colony-print<=0.21.0"]])
        self.assertEqual(
            sorted(os.listdir(self.packages_path)), [APPIER_NAME, WHEEL_NAME]
        )
        self.assertEqual(
            self._read(os.path.join(self.packages_path, WHEEL_NAME)), b"colony-print"
        )

        # runs the update once more with the new version installed, which
        # must neither download (already mirrored) nor install any package
        MockUrllibRequest.requests = []
        MockSubprocess.calls = []
        self._installed(colony_print="0.21.0", appier="1.40.0")
        requirements = self.boot.update(self.packages_path)
        self.assertEqual(requirements, [])
        self.assertEqual(self._urls(), ["https://print.example.com/packages"])
        self.assertEqual(MockSubprocess.calls, [])

    def test_update_rollback(self):
        # the newer version is removed from the server, so the (older) one
        # that is left must be installed, replacing the installed one
        MockUrllibRequest.files["colony_print-0.20.0-py2.py3-none-any.whl"] = b"old"
        self._installed(colony_print="0.21.0")
        requirements = self.boot.update(self.packages_path)
        self.assertEqual(requirements, [("colony-print", "0.20.0")])
        self.assertEqual(self._requirements(), [["colony-print<=0.20.0"]])

    def test_update_empty(self):
        self._installed(colony_print="0.20.0")
        requirements = self.boot.update(self.packages_path)
        self.assertEqual(requirements, [])
        self.assertEqual(os.listdir(self.packages_path), [])
        self.assertEqual(MockSubprocess.calls, [])

    def test_update_install_error(self):
        MockUrllibRequest.files[WHEEL_NAME] = b"colony-print"
        MockSubprocess.code = 2
        self._installed(colony_print="0.20.0")
        self.assertRaises(RuntimeError, lambda: self.boot.update(self.packages_path))

    def test_update_insecure(self):
        # the packages are installed and run by the service, so they're not
        # retrieved through plain HTTP from another machine, unless allowed
        MockUrllibRequest.files[WHEEL_NAME] = b"colony-print"
        self._installed(colony_print="0.20.0")
        self.environ["BASE_URL"] = "http://print.example.com/"
        self.assertEqual(self.boot.update(self.packages_path), [])
        self.assertEqual(MockUrllibRequest.requests, [])
        self.assertEqual(MockSubprocess.calls, [])

        self.environ["NODE_UPDATE_INSECURE"] = "1"
        requirements = self.boot.update(self.packages_path)
        self.assertEqual(requirements, [("colony-print", "0.21.0")])

    def test_fetch_packages(self):
        MockUrllibRequest.listing = [
            dict(file=APPIER_NAME, sha256="digest"),
            dict(file="../" + APPIER_NAME),
            dict(file="..\\" + APPIER_NAME),
            dict(file="appier.txt"),
            dict(file=None),
            dict(file=10),
            dict(file=[APPIER_NAME]),
            dict(name="appier"),
            APPIER_NAME,
            None,
        ]
        self.assertEqual(
            self.boot.fetch_packages(), [dict(file=APPIER_NAME, sha256="digest")]
        )

        request, timeout = MockUrllibRequest.requests[0]
        self.assertEqual(request.url, "https://print.example.com/packages")
        self.assertEqual(timeout, colony_print.boot.TIMEOUT)

        MockUrllibRequest.listing = dict(result="success")
        self.assertRaises(ValueError, self.boot.fetch_packages)

    def test_fetch_packages_retry(self):
        # the errors reaching the server (eg: network not ready on boot)
        # are retried, while the ones returned by the server are not
        MockUrllibRequest.listing = []
        MockUrllibRequest.errors = [IOError("Unreachable"), IOError("Unreachable")]
        self.assertEqual(self.boot.fetch_packages(), [])
        self.assertEqual(len(MockUrllibRequest.requests), 3)

        MockUrllibRequest.requests = []
        MockUrllibRequest.errors = [IOError("Unreachable")] * 3
        self.assertRaises(IOError, self.boot.fetch_packages)
        self.assertEqual(len(MockUrllibRequest.requests), 3)

        MockUrllibRequest.requests = []
        MockUrllibRequest.errors = [MockHTTPError("Not Found")]
        self.assertRaises(MockHTTPError, self.boot.fetch_packages)
        self.assertEqual(len(MockUrllibRequest.requests), 1)

        boot = colony_print.boot.ColonyPrintBoot(
            environ=self.environ, retries=1, retry_delay=0.0
        )
        MockUrllibRequest.requests = []
        MockUrllibRequest.errors = [IOError("Unreachable")]
        self.assertRaises(IOError, boot.fetch_packages)
        self.assertEqual(len(MockUrllibRequest.requests), 1)

        # no retries still means one attempt to reach the server, raising
        # its error (and not an error of the retrying itself) on failure
        boot = colony_print.boot.ColonyPrintBoot(
            environ=self.environ, retries=0, retry_delay=0.0
        )
        MockUrllibRequest.requests = []
        self.assertEqual(boot.fetch_packages(), [])
        self.assertEqual(len(MockUrllibRequest.requests), 1)

        MockUrllibRequest.requests = []
        MockUrllibRequest.errors = [IOError("Unreachable")]
        self.assertRaises(IOError, boot.fetch_packages)
        self.assertEqual(len(MockUrllibRequest.requests), 1)

    def test_sync(self):
        MockUrllibRequest.files[WHEEL_NAME] = b"colony-print"
        MockUrllibRequest.files[APPIER_NAME] = b"appier"
        packages = self.boot.fetch_packages()
        MockUrllibRequest.requests = []

        # the packages directory holds a changed (corrupted) package that
        # must be downloaded again, a stale package and a stale temporary
        # file that must be removed and a file (not a package) that is not
        # managed by the boot, and so must be kept
        os.makedirs(self.packages_path)
        self._write(os.path.join(self.packages_path, APPIER_NAME), b"corrupted")
        self._write(
            os.path.join(self.packages_path, "appier-1.39.0-py3-none-any.whl"),
            b"stale",
        )
        self._write(os.path.join(self.packages_path, WHEEL_NAME + ".tmp"), b"temp")
        self._write(os.path.join(self.packages_path, "notes.txt"), b"notes")

        self.boot.sync(self.packages_path, packages)
        self.assertEqual(
            sorted(os.listdir(self.packages_path)),
            [APPIER_NAME, WHEEL_NAME, "notes.txt"],
        )
        self.assertEqual(
            self._read(os.path.join(self.packages_path, APPIER_NAME)), b"appier"
        )
        self.assertEqual(len(MockUrllibRequest.requests), 2)

        MockUrllibRequest.requests = []
        self.boot.sync(self.packages_path, packages)
        self.assertEqual(MockUrllibRequest.requests, [])

        # a package listed without digest is only downloaded when missing,
        # as there's no way of verifying the existing one
        self._write(os.path.join(self.packages_path, APPIER_NAME), b"unknown")
        self.boot.sync(self.packages_path, [dict(file=APPIER_NAME)])
        self.assertEqual(MockUrllibRequest.requests, [])
        self.assertEqual(
            sorted(os.listdir(self.packages_path)), [APPIER_NAME, "notes.txt"]
        )

        self.boot.sync(self.packages_path, [])
        self.assertEqual(os.listdir(self.packages_path), ["notes.txt"])

    def test_download(self):
        data = b"appier" * colony_print.boot.CHUNK_SIZE
        MockUrllibRequest.files[APPIER_NAME] = data
        os.makedirs(self.packages_path)
        file_path = os.path.join(self.packages_path, APPIER_NAME)

        self.boot.download(
            APPIER_NAME, file_path, sha256=hashlib.sha256(data).hexdigest()
        )
        self.assertEqual(self._read(file_path), data)
        self.assertEqual(os.listdir(self.packages_path), [APPIER_NAME])
        self.assertEqual(MockUrllibRequest.responses[0].closed, True)

        request, timeout = MockUrllibRequest.requests[0]
        self.assertEqual(
            request.url, "https://print.example.com/packages/" + APPIER_NAME
        )
        self.assertEqual(request.headers["X-Secret-Key"], "key")
        self.assertEqual(timeout, colony_print.boot.DOWNLOAD_TIMEOUT)

        # replaces the existing package when no digest is provided
        MockUrllibRequest.files[APPIER_NAME] = b"other"
        self.boot.download(APPIER_NAME, file_path)
        self.assertEqual(self._read(file_path), b"other")

    def test_download_digest(self):
        # a package that doesn't match its digest must not replace the
        # existing one, nor leave any temporary file behind
        MockUrllibRequest.files[APPIER_NAME] = b"tampered"
        os.makedirs(self.packages_path)
        file_path = os.path.join(self.packages_path, APPIER_NAME)
        self._write(file_path, b"appier")

        self.assertRaises(
            ValueError,
            lambda: self.boot.download(
                APPIER_NAME, file_path, sha256=hashlib.sha256(b"appier").hexdigest()
            ),
        )
        self.assertEqual(os.listdir(self.packages_path), [APPIER_NAME])
        self.assertEqual(self._read(file_path), b"appier")
        self.assertEqual(MockUrllibRequest.responses[0].closed, True)

    def test_download_error(self):
        # a download interrupted by a lost connection must not leave any
        # temporary file behind, nor replace the existing package
        MockUrllibRequest.files[APPIER_NAME] = b"appier" * colony_print.boot.CHUNK_SIZE
        MockUrllibRequest.broken = True
        os.makedirs(self.packages_path)
        file_path = os.path.join(self.packages_path, APPIER_NAME)
        self._write(file_path, b"appier")

        self.assertRaises(IOError, lambda: self.boot.download(APPIER_NAME, file_path))
        self.assertEqual(os.listdir(self.packages_path), [APPIER_NAME])
        self.assertEqual(self._read(file_path), b"appier")
        self.assertEqual(MockUrllibRequest.responses[0].closed, True)

    def test_select(self):
        versions = self.boot.select(
            [
                dict(file="colony_print-0.21.0-py2.py3-none-any.whl"),
                dict(file="colony_print-0.20.0-py2.py3-none-any.whl"),
                dict(file="colony_print-0.21.0rc1-py2.py3-none-any.whl"),
                dict(file="Colony_Print-0.19.0-py2.py3-none-any.whl"),
                dict(file="npcolony-1.9.0-cp314-cp314-win_amd64.whl"),
                dict(file="npcolony-1.10.0-cp314-cp314-win_amd64.whl"),
                dict(file="npcolony-1.10.0-cp313-cp313-win_amd64.whl"),
                dict(file="Gravo.Pilot-1.0.0_rc1-py3-none-any.whl"),
            ]
        )
        self.assertEqual(
            versions,
            {
                "colony-print": "0.21.0",
                "npcolony": "1.10.0",
                "gravo-pilot": "1.0.0-rc1",
            },
        )
        self.assertEqual(self.boot.select([]), dict())

    def test_outdated(self):
        self._installed(colony_print="0.21.0", pillow="11.0.0", appier="1.40.0")
        requirements = self.boot.outdated(
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
        self.assertEqual(self.boot.outdated(dict()), [])

    def test_install(self):
        self.boot.install(
            self.packages_path,
            [("colony-print", "0.21.0"), ("npcolony", "1.3.0+win"), ("pip", "26.0rc1")],
        )
        self.assertEqual(
            MockSubprocess.calls,
            [
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--upgrade",
                    "--no-index",
                    "--find-links",
                    self.packages_path,
                    "--only-binary",
                    ":all:",
                    "--disable-pip-version-check",
                    "--no-warn-script-location",
                    "--no-input",
                    "colony-print<=0.21.0",
                    "npcolony<=1.3.0",
                    "pip<=26.0rc1",
                ]
            ],
        )

        MockSubprocess.code = 1
        self.assertRaises(
            RuntimeError,
            lambda: self.boot.install(self.packages_path, [("npcolony", "1.3.0")]),
        )

    def test_compatible(self):
        major, minor = sys.version_info[0], sys.version_info[1]
        _pairs, platforms = self.boot.tags
        platform = sorted(platforms - set(["any"]))[0]
        abi = self.boot.abi(major, minor)
        compatible = lambda file: self.boot.compatible(dict(file=file))

        self.assertEqual(compatible(WHEEL_NAME), True)
        self.assertEqual(compatible("appier-1.40.0-py%d-none-any.whl" % major), True)
        self.assertEqual(
            compatible(
                "npcolony-1.3.0-cp%d%d-%s-%s.whl" % (major, minor, abi, platform)
            ),
            True,
        )
        self.assertEqual(
            compatible(
                "npcolony-1.3.0-cp%d%d-cp%d%d-%s.whl"
                % (major, minor + 1, major, minor + 1, platform)
            ),
            False,
        )
        self.assertEqual(
            compatible(
                "npcolony-1.3.0-cp%d%d-cp%d%d-solaris_2_11_sparc.whl"
                % (major, minor, major, minor)
            ),
            False,
        )
        self.assertEqual(
            compatible("appier-1.40.0-py%d-none-any.whl" % (major + 1)), False
        )
        self.assertEqual(compatible("colony_print-0.21.0.zip"), False)
        self.assertEqual(compatible("../" + WHEEL_NAME), False)
        self.assertEqual(self.boot.compatible(dict()), False)
        self.assertEqual(self.boot.compatible(dict(file=10)), False)

        # the wheels built for the stable ABI (abi3) of an older version and
        # the pure ones for an older version are installed by pip as well
        if major == 3 and minor > 2:
            self.assertEqual(compatible("cffi-2.0.0-cp32-abi3-%s.whl" % platform), True)
            self.assertEqual(
                compatible("cffi-2.0.0-cp32-cp32m-%s.whl" % platform), False
            )
            self.assertEqual(
                compatible("six-1.17.0-py%d%d-none-any.whl" % (major, minor - 1)),
                True,
            )
            self.assertEqual(
                compatible(
                    "cffi-2.0.0-cp%d%d-abi3-%s.whl" % (major, minor + 1, platform)
                ),
                False,
            )

    def test_installed_version(self):
        boot = colony_print.boot.ColonyPrintBoot(environ=dict())
        version = boot.installed_version("appier")
        self.assertNotEqual(version, None)
        self.assertEqual(boot.version_key(version)[0] >= 0, True)
        self.assertEqual(boot.installed_version("colony-print-missing"), None)

    def test_load_config(self):
        self.assertEqual(self.boot.load_config(self.config_path), dict())

        self._write(
            self.config_path,
            codecs.BOM_UTF8
            + b"# Colony Print node\r\n"
            + b"BASE_URL=https://print.example.com/\r\n"
            + b"SECRET_KEY = secret=key \r\n"
            + b'NODE_NAME="Shop \\"1\\""\r\n'
            + b"NODE_LOCATION='Porto'\r\n"
            + b'NODE_PRINTER="\r\n'
            + b"\r\n"
            + b"INVALID\r\n"
            + b"=value\r\n"
            + b"NODE_EMAIL_RECEIVERS=a@example.com;b@example.com\r\n"
            + b"NODE_ID=first\n"
            + b"NODE_ID=second\n"
            + appier.legacy.u("NODE_LABEL=São João\r\n").encode("utf-8"),
        )
        self.assertEqual(
            self.boot.load_config(self.config_path),
            dict(
                BASE_URL="https://print.example.com/",
                SECRET_KEY="secret=key",
                NODE_NAME='Shop "1"',
                NODE_LOCATION="Porto",
                NODE_PRINTER='"',
                NODE_EMAIL_RECEIVERS="a@example.com;b@example.com",
                NODE_ID="second",
                NODE_LABEL=appier.legacy.u("São João"),
            ),
        )

    def test_apply_config(self):
        environ = dict(BASE_URL="https://other.example.com/")
        boot = colony_print.boot.ColonyPrintBoot(environ=environ)
        boot.apply_config(dict(BASE_URL="https://print.example.com/", SECRET_KEY="key"))
        self.assertEqual(
            environ, dict(BASE_URL="https://other.example.com/", SECRET_KEY="key")
        )

    def test_request(self):
        MockUrllibRequest.files[APPIER_NAME] = b"appier"
        data = self.boot.request(
            "https://print.example.com/packages/" + APPIER_NAME, timeout=5.0
        )
        self.assertEqual(data, b"appier")
        self.assertEqual(MockUrllibRequest.requests[0][1], 5.0)
        self.assertEqual(MockUrllibRequest.responses[0].closed, True)

    def test_open(self):
        self.boot.open("https://print.example.com/packages").close()
        request, timeout = MockUrllibRequest.requests[0]
        self.assertEqual(request.url, "https://print.example.com/packages")
        self.assertEqual(
            request.headers,
            {"User-Agent": colony_print.boot.NAME, "X-Secret-Key": "key"},
        )
        self.assertEqual(timeout, colony_print.boot.TIMEOUT)

        self.assertEqual(len(MockUrllibRequest.handlers), 1)
        self.assertEqual(
            isinstance(
                MockUrllibRequest.handlers[0], colony_print.boot.SecretRedirectHandler
            ),
            True,
        )

        boot = colony_print.boot.ColonyPrintBoot(environ=dict(SECRET_KEY=""))
        boot.open("https://print.example.com/packages").close()
        request, _timeout = MockUrllibRequest.requests[1]
        self.assertEqual(request.headers, {"User-Agent": colony_print.boot.NAME})

        # the secret key is only sent to the server (the origin of the base
        # URL) and not to the other hosts (eg: the ones of the packages)
        for url in (
            "https://cdn.example.com/packages",
            "http://print.example.com/packages",
            "https://print.example.com:8443/packages",
        ):
            self.boot.open(url).close()
            request, _timeout = MockUrllibRequest.requests[-1]
            self.assertEqual(request.url, url)
            self.assertEqual(request.headers, {"User-Agent": colony_print.boot.NAME})

    def test_same_origin(self):
        same_origin = self.boot.same_origin
        self.assertEqual(
            same_origin(
                "https://print.example.com/packages", "https://print.example.com/"
            ),
            True,
        )
        self.assertEqual(
            same_origin(
                "https://Print.Example.com:443/a", "https://print.example.com/b"
            ),
            True,
        )
        self.assertEqual(
            same_origin("http://localhost:8080/packages", "http://localhost:8080/"),
            True,
        )
        self.assertEqual(
            same_origin("http://print.example.com/", "https://print.example.com/"),
            False,
        )
        self.assertEqual(
            same_origin("https://cdn.example.com/", "https://print.example.com/"),
            False,
        )
        self.assertEqual(
            same_origin(
                "https://print.example.com:8443/", "https://print.example.com/"
            ),
            False,
        )
        self.assertEqual(
            same_origin(
                "https://print.example.com.evil.com/", "https://print.example.com/"
            ),
            False,
        )

    def test_digest(self):
        file_path = os.path.join(self.temp_path, APPIER_NAME)
        data = b"appier" * colony_print.boot.CHUNK_SIZE
        self._write(file_path, data)
        self.assertEqual(self.boot.digest(file_path), hashlib.sha256(data).hexdigest())

        self._write(file_path, b"")
        self.assertEqual(self.boot.digest(file_path), hashlib.sha256(b"").hexdigest())

    def test_match_wheel(self):
        match = self.boot.match_wheel("npcolony-1.3.0-1-cp314-cp314-win_amd64.whl")
        self.assertEqual(match.group("name"), "npcolony")
        self.assertEqual(match.group("version"), "1.3.0")
        self.assertEqual(match.group("build"), "1")
        self.assertEqual(match.group("python"), "cp314")
        self.assertEqual(match.group("abi"), "cp314")
        self.assertEqual(match.group("platform"), "win_amd64")

        match = self.boot.match_wheel(WHEEL_NAME)
        self.assertEqual(match.group("build"), None)
        self.assertEqual(match.group("python"), "py2.py3")

        self.assertEqual(self.boot.match_wheel("colony_print-0.21.0.tar.gz"), None)
        self.assertEqual(self.boot.match_wheel("colony_print-py3-none-any.whl"), None)
        self.assertEqual(self.boot.match_wheel("../" + WHEEL_NAME), None)
        self.assertEqual(self.boot.match_wheel("..\\" + WHEEL_NAME), None)
        self.assertEqual(self.boot.match_wheel("dir/" + WHEEL_NAME), None)
        self.assertEqual(self.boot.match_wheel(WHEEL_NAME + "\n"), None)
        self.assertEqual(self.boot.match_wheel(""), None)
        self.assertEqual(self.boot.match_wheel(None), None)
        self.assertEqual(self.boot.match_wheel(10), None)

    def test_normalize(self):
        self.assertEqual(self.boot.normalize("colony_print"), "colony-print")
        self.assertEqual(self.boot.normalize("Gravo.Pilot"), "gravo-pilot")
        self.assertEqual(self.boot.normalize("mailme__api"), "mailme-api")
        self.assertEqual(self.boot.normalize("appier"), "appier")

    def test_version_key(self):
        versions = [
            "",
            "1.0.0+",
            "invalid",
            "0.9",
            "1.0.0.dev1",
            "1.0.0a1.dev1",
            "1.0.0a1",
            "1.0.0b2",
            "1.0.0rc1",
            "1.0.0rc1.post1",
            "1.0.0",
            "1.0.0+local",
            "1.0.0+local.1",
            "1.0.0+2",
            "1.0.0+10",
            "1.0.0.post1.dev1",
            "1.0.0.post1",
            "1.0.0.post2",
            "1.0.1",
            "1.2",
            "1.10",
            "2!0.1",
        ]
        keys = [self.boot.version_key(version) for version in versions]
        self.assertEqual(keys, sorted(keys))
        self.assertEqual(len(set(keys)), len(keys))
        for version, other in (
            ("1.0", "1.0.0"),
            ("0", "0.0"),
            ("1.0.0-rc1", "1.0.0rc1"),
            ("1.0.0_rc1", "1.0.0rc1"),
            ("1.0.0RC1", "1.0.0rc1"),
            ("1.0.0c1", "1.0.0rc1"),
            ("1.0.0alpha1", "1.0.0a1"),
            ("1.0.0a", "1.0.0a0"),
            ("1.0.0-1", "1.0.0.post1"),
            ("1.0.0.rev1", "1.0.0.post1"),
            ("1.0.0.post", "1.0.0.post0"),
            ("1.0.0dev", "1.0.0.dev0"),
            ("1.0.0+Local_1", "1.0.0+local.1"),
            ("1.0.0+02", "1.0.0+2"),
            (" v1.0 ", "1.0"),
        ):
            self.assertEqual(
                self.boot.version_key(version), self.boot.version_key(other)
            )
        self.assertEqual(
            self.boot.version_key("1.0\n") == self.boot.version_key("1.0"), True
        )
        self.assertEqual(
            self.boot.version_key("1.0.0\n+2") < self.boot.version_key("0"), True
        )

    def test_abi(self):
        self.assertEqual(self.boot.abi(3, 14), "cp314")
        self.assertEqual(self.boot.abi(3, 8), "cp38")
        self.assertEqual(self.boot.abi(3, 7), "cp37m")
        self.assertEqual(self.boot.abi(3, 3), "cp33m")
        self.assertEqual(
            self.boot.abi(2, 7), "cp27mu" if sys.maxunicode == 0x10FFFF else "cp27m"
        )

    def test_tags(self):
        major, minor = sys.version_info[0], sys.version_info[1]
        pairs, platforms = self.boot.tags
        current = "cp%d%d" % (major, minor)
        abi = self.boot.abi(major, minor)
        self.assertEqual((current, abi) in pairs, True)
        self.assertEqual((current, "none") in pairs, True)
        self.assertEqual(("py%d" % major, "none") in pairs, True)
        self.assertEqual(("py%d%d" % (major, minor), "none") in pairs, True)
        self.assertEqual(("py%d" % major, current) in pairs, False)
        self.assertEqual("any" in platforms, True)
        self.assertEqual(len(platforms), 2)
        for platform in platforms:
            self.assertEqual("-" in platform or "." in platform, False)

    def test_base_url(self):
        boot = colony_print.boot.ColonyPrintBoot(environ=dict())
        self.assertEqual(boot.base_url, colony_print.boot.BASE_URL)

        boot = colony_print.boot.ColonyPrintBoot(environ=dict(BASE_URL=""))
        self.assertEqual(boot.base_url, colony_print.boot.BASE_URL)

        boot = colony_print.boot.ColonyPrintBoot(
            environ=dict(BASE_URL="http://localhost:8080")
        )
        self.assertEqual(boot.base_url, "http://localhost:8080/")

        boot = colony_print.boot.ColonyPrintBoot(
            environ=dict(BASE_URL="http://localhost:8080/")
        )
        self.assertEqual(boot.base_url, "http://localhost:8080/")

    def test_packages_url(self):
        boot = colony_print.boot.ColonyPrintBoot(environ=dict())
        self.assertEqual(boot.packages_url, colony_print.boot.BASE_URL + "packages")

        boot = colony_print.boot.ColonyPrintBoot(
            environ=dict(BASE_URL="http://localhost:8080")
        )
        self.assertEqual(boot.packages_url, "http://localhost:8080/packages")

        boot = colony_print.boot.ColonyPrintBoot(
            environ=dict(
                BASE_URL="http://localhost:8080",
                PACKAGES_URL="http://localhost:9090/repo/",
            )
        )
        self.assertEqual(boot.packages_url, "http://localhost:9090/repo")

    def test_packages_secure(self):
        for base_url in (
            "https://print.example.com/",
            "http://localhost:8686/",
            "http://127.0.0.1:8686/",
            "http://[::1]:8686/",
        ):
            boot = colony_print.boot.ColonyPrintBoot(environ=dict(BASE_URL=base_url))
            self.assertEqual(boot.packages_secure, True)

        for base_url in (
            "http://print.example.com/",
            "http://192.168.1.10:8686/",
            "http://localhost.example.com/",
            "http://127.evil.example.com/",
            "http://127.0.0.1.evil.example.com/",
            "ftp://print.example.com/",
        ):
            boot = colony_print.boot.ColonyPrintBoot(environ=dict(BASE_URL=base_url))
            self.assertEqual(boot.packages_secure, False)

        # the packages URL decides, not the base URL, and the insecure update
        # is only allowed with an explicit (true) value
        boot = colony_print.boot.ColonyPrintBoot(
            environ=dict(
                BASE_URL="https://print.example.com/",
                PACKAGES_URL="http://packages.example.com/",
            )
        )
        self.assertEqual(boot.packages_secure, False)
        for value, secure in (("1", True), ("true", True), ("0", False), ("", False)):
            boot = colony_print.boot.ColonyPrintBoot(
                environ=dict(
                    BASE_URL="http://print.example.com/", NODE_UPDATE_INSECURE=value
                )
            )
            self.assertEqual(boot.packages_secure, secure)

    def test_update_enabled(self):
        boot = colony_print.boot.ColonyPrintBoot(environ=dict())
        self.assertEqual(boot.update_enabled, True)

        for value in ("0", "false", "False", "no", " off "):
            boot = colony_print.boot.ColonyPrintBoot(environ=dict(NODE_UPDATE=value))
            self.assertEqual(boot.update_enabled, False)

        for value in ("1", "true", "yes", ""):
            boot = colony_print.boot.ColonyPrintBoot(environ=dict(NODE_UPDATE=value))
            self.assertEqual(boot.update_enabled, True)
