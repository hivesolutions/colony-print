#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import codecs
import shutil
import logging
import tempfile
import unittest

import appier

import colony_print.boot
import colony_print.node

PIP_COMMAND = [
    sys.executable,
    "-m",
    "pip",
    "install",
    "--upgrade",
    "--only-binary",
    ":all:",
    "--no-cache-dir",
    "--disable-pip-version-check",
    "--no-warn-script-location",
    "--no-input",
]
""" The command (without the requirements) that is expected to be
run by the boot for the update of the packages of the node """

INDEX_COMMAND = [
    sys.executable,
    "-m",
    "pip",
    "index",
    "versions",
    "colony-print",
    "--timeout",
    "10",
    "--retries",
    "1",
    "--disable-pip-version-check",
    "--no-input",
]
""" The command that is expected to be run by the boot to verify that
the package index is reachable, before each attempt of the update """


class MockSubprocess(object):
    """
    Stand-in for the subprocess module that records the commands that
    are called (and their environments) and returns the configured exit
    codes (one for each call, the last one being kept) or raises the
    configured error, so that the update of the packages can be exercised
    without pip.
    """

    codes = [0]
    error = None
    calls = []
    envs = []

    @staticmethod
    def call(command, env=None):
        MockSubprocess.calls.append(command)
        MockSubprocess.envs.append(env)
        if MockSubprocess.error:
            raise MockSubprocess.error
        if len(MockSubprocess.codes) > 1:
            return MockSubprocess.codes.pop(0)
        return MockSubprocess.codes[0]


class MockLoggingHandler(logging.Handler):
    """
    Logging handler that keeps the records that are logged, so that the
    messages logged by the boot (and their levels) can be verified.
    """

    def __init__(self):
        logging.Handler.__init__(self)
        self.records = []

    def emit(self, record):
        self.records.append(record)


class MockColonyPrintNode(object):
    """
    Stand-in for the node that counts the loops run on it, so that the
    running of the node by the boot can be exercised without a server.
    """

    loops = 0

    def loop(self):
        MockColonyPrintNode.loops += 1


class ColonyPrintBootTest(unittest.TestCase):
    def setUp(self):
        self.environ = dict(BASE_URL="https://print.example.com/", SECRET_KEY="key")
        self.boot = colony_print.boot.ColonyPrintBoot(
            environ=self.environ, retry_delay=0.0
        )
        self.temp_path = tempfile.mkdtemp(prefix="colony-print-boot-test-")
        self.config_path = os.path.join(self.temp_path, "config.env")
        MockSubprocess.codes = [0]
        MockSubprocess.error = None
        MockSubprocess.calls = []
        MockSubprocess.envs = []
        MockColonyPrintNode.loops = 0
        self._subprocess = colony_print.boot.subprocess
        colony_print.boot.subprocess = MockSubprocess
        self._node = colony_print.node.ColonyPrintNode
        colony_print.node.ColonyPrintNode = MockColonyPrintNode

    def tearDown(self):
        shutil.rmtree(self.temp_path, ignore_errors=True)
        colony_print.boot.subprocess = self._subprocess
        colony_print.node.ColonyPrintNode = self._node

    def _write(self, path, data):
        with open(path, "wb") as file:
            file.write(data)

    def _requirements(self):
        return [
            command[len(PIP_COMMAND) :]
            for command in MockSubprocess.calls
            if command[: len(PIP_COMMAND)] == PIP_COMMAND
        ]

    def test_main(self):
        self._write(
            self.config_path,
            b"BASE_URL=https://print.example.com\r\n"
            + b"SECRET_KEY=secret\r\n"
            + b"NODE_VERSION=0.21.0\r\n",
        )
        environ = dict()
        boot = colony_print.boot.ColonyPrintBoot(environ=environ, retry_delay=0.0)

        boot.main(["--config", self.config_path])
        self.assertEqual(environ["BASE_URL"], "https://print.example.com/")
        self.assertEqual(environ["SECRET_KEY"], "secret")
        self.assertEqual(
            MockSubprocess.calls,
            [INDEX_COMMAND, PIP_COMMAND + ["colony-print==0.21.0", "npcolony"]],
        )
        self.assertEqual(MockColonyPrintNode.loops, 1)

    def test_main_config_default(self):
        self._write(self.config_path, b"NODE_UPDATE=0\r\nNODE_NAME=Shop\r\n")
        environ = dict(COLONY_PRINT_CONFIG=self.config_path)
        boot = colony_print.boot.ColonyPrintBoot(environ=environ, retry_delay=0.0)

        boot.main([])
        self.assertEqual(environ["NODE_NAME"], "Shop")
        self.assertEqual(environ["BASE_URL"], colony_print.boot.BASE_URL)
        self.assertEqual(MockSubprocess.calls, [])
        self.assertEqual(MockColonyPrintNode.loops, 1)

    def test_main_config_missing(self):
        self.boot.main(["--config", self.config_path, "--no-update"])
        self.assertEqual(self.environ["BASE_URL"], "https://print.example.com/")
        self.assertEqual(MockColonyPrintNode.loops, 1)

    def test_main_no_update(self):
        self.boot.main(["--config", self.config_path, "--no-update"])
        self.assertEqual(MockSubprocess.calls, [])
        self.assertEqual(MockColonyPrintNode.loops, 1)

    def test_main_update_only(self):
        self.boot.main(["--config", self.config_path, "--update-only"])
        self.assertEqual(self._requirements(), [["colony-print", "npcolony"]])
        self.assertEqual(MockColonyPrintNode.loops, 0)

    def test_main_update_disabled(self):
        self._write(self.config_path, b"NODE_UPDATE=false\r\n")
        self.boot.main(["--config", self.config_path])
        self.assertEqual(MockSubprocess.calls, [])
        self.assertEqual(MockColonyPrintNode.loops, 1)

    def test_main_update_error(self):
        # makes sure that a failed update (pip failing on every attempt or
        # not even running) only logs a warning and never prevents the node
        # from running (with the installed packages), notice that the level
        # of the root logger is set as it's changed by the apps of the tests
        handler = MockLoggingHandler()
        logger = logging.getLogger()
        level = logger.level
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        try:
            MockSubprocess.codes = [1]
            self.boot.main(["--config", self.config_path])
            self.assertEqual(len(MockSubprocess.calls), colony_print.boot.RETRIES)
            self.assertEqual(MockColonyPrintNode.loops, 1)

            MockSubprocess.calls = []
            MockSubprocess.error = OSError("No such file or directory")
            self.boot.main(["--config", self.config_path])
            self.assertEqual(len(MockSubprocess.calls), 1)
            self.assertEqual(MockColonyPrintNode.loops, 2)
        finally:
            logger.removeHandler(handler)
            logger.setLevel(level)

        problems = [
            record
            for record in handler.records
            if "Problem updating node" in record.getMessage()
        ]
        self.assertEqual(len(problems), 2)
        self.assertEqual([record.levelno for record in problems], [logging.WARNING] * 2)
        self.assertEqual(
            "Package update failed with code 1" in problems[0].getMessage(), True
        )
        self.assertEqual("No such file or directory" in problems[1].getMessage(), True)
        self.assertEqual(
            [record for record in handler.records if record.levelno > logging.WARNING],
            [],
        )

    def test_run(self):
        self.boot.run()
        self.assertEqual(MockColonyPrintNode.loops, 1)

    def test_update(self):
        requirements = self.boot.update()
        self.assertEqual(requirements, ["colony-print", "npcolony"])
        self.assertEqual(
            MockSubprocess.calls,
            [INDEX_COMMAND, PIP_COMMAND + ["colony-print", "npcolony"]],
        )

        # pip runs with the environment of the node (eg: with its PIP_* values)
        # but without any of its configuration files, as its global one may be
        # created by any user, leaving the environment of the node unchanged
        for env in MockSubprocess.envs:
            self.assertEqual(env["PIP_CONFIG_FILE"], os.devnull)
            self.assertEqual(env["SECRET_KEY"], "key")
        self.assertEqual("PIP_CONFIG_FILE" in self.environ, False)

        self.environ.update(PIP_CONFIG_FILE="pip.ini", PIP_PROXY="http://proxy:8080")
        MockSubprocess.envs = []
        self.boot.update()
        for env in MockSubprocess.envs:
            self.assertEqual(env["PIP_CONFIG_FILE"], os.devnull)
            self.assertEqual(env["PIP_PROXY"], "http://proxy:8080")
        del self.environ["PIP_CONFIG_FILE"]
        del self.environ["PIP_PROXY"]

        # the versions of the packages are constrained (pinned or rolled back)
        # by the configuration and the packages are retrieved from the custom
        # index, when defined, instead of PyPI
        self.environ.update(
            NODE_VERSION="0.20.0",
            NODE_NPCOLONY_VERSION="<1.5",
            NODE_INDEX_URL="https://pypi.example.com/simple/",
        )
        MockSubprocess.calls = []
        requirements = self.boot.update()
        self.assertEqual(requirements, ["colony-print==0.20.0", "npcolony<1.5"])
        self.assertEqual(
            MockSubprocess.calls,
            [
                INDEX_COMMAND + ["--index-url", "https://pypi.example.com/simple/"],
                PIP_COMMAND
                + ["--index-url", "https://pypi.example.com/simple/"]
                + ["colony-print==0.20.0", "npcolony<1.5"],
            ],
        )

    def test_update_retry(self):
        # the update is retried while the package index is not reachable (as
        # pip would keep the installed packages, exiting with success) or the
        # install fails, as the network may not be ready when the node boots,
        # stopping at the first success
        MockSubprocess.codes = [1, 0, 2, 0, 0]
        self.assertEqual(self.boot.update(), ["colony-print", "npcolony"])
        self.assertEqual(
            MockSubprocess.calls,
            [
                INDEX_COMMAND,
                INDEX_COMMAND,
                PIP_COMMAND + ["colony-print", "npcolony"],
                INDEX_COMMAND,
                PIP_COMMAND + ["colony-print", "npcolony"],
            ],
        )

        # an index that is never reachable fails the update without trying
        # to install the packages (as pip would succeed without the index)
        MockSubprocess.codes = [1]
        MockSubprocess.calls = []
        with self.assertRaises(RuntimeError) as context:
            self.boot.update()
        self.assertEqual(str(context.exception), "Package update failed with code 1")
        self.assertEqual(
            MockSubprocess.calls, [INDEX_COMMAND] * colony_print.boot.RETRIES
        )

        MockSubprocess.codes = [0, 2] * colony_print.boot.RETRIES
        MockSubprocess.calls = []
        with self.assertRaises(RuntimeError) as context:
            self.boot.update()
        self.assertEqual(str(context.exception), "Package update failed with code 2")
        self.assertEqual(len(MockSubprocess.calls), 2 * colony_print.boot.RETRIES)

        # there's always (at least) one attempt, even without retries
        boot = colony_print.boot.ColonyPrintBoot(
            environ=self.environ, retries=0, retry_delay=0.0
        )
        MockSubprocess.calls = []
        self.assertRaises(RuntimeError, boot.update)
        self.assertEqual(len(MockSubprocess.calls), 1)

    def test_requirement(self):
        requirement = self.boot.requirement
        self.assertEqual(requirement("colony-print", None), "colony-print")
        self.assertEqual(requirement("colony-print", ""), "colony-print")
        self.assertEqual(requirement("colony-print", "  "), "colony-print")
        self.assertEqual(requirement("colony-print", "0.21.0"), "colony-print==0.21.0")
        self.assertEqual(
            requirement("colony-print", " 0.21.* "), "colony-print==0.21.*"
        )
        for constraint in ("==0.21.0", "<0.22", ">=0.20,<0.22", "!=0.21.1", "~=0.21"):
            self.assertEqual(
                requirement("colony-print", constraint), "colony-print" + constraint
            )

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

    def test_requirements(self):
        self.assertEqual(self.boot.requirements, ["colony-print", "npcolony"])

        self.environ.update(NODE_VERSION="0.21.0", NODE_NPCOLONY_VERSION=">=1.4.0")
        self.assertEqual(
            self.boot.requirements, ["colony-print==0.21.0", "npcolony>=1.4.0"]
        )

        self.environ.update(NODE_VERSION="", NODE_NPCOLONY_VERSION="1.4.0")
        self.assertEqual(self.boot.requirements, ["colony-print", "npcolony==1.4.0"])

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

    def test_index_url(self):
        boot = colony_print.boot.ColonyPrintBoot(environ=dict())
        self.assertEqual(boot.index_url, None)

        for value in ("", "  "):
            boot = colony_print.boot.ColonyPrintBoot(environ=dict(NODE_INDEX_URL=value))
            self.assertEqual(boot.index_url, None)

        boot = colony_print.boot.ColonyPrintBoot(
            environ=dict(NODE_INDEX_URL=" https://pypi.example.com/simple/ ")
        )
        self.assertEqual(boot.index_url, "https://pypi.example.com/simple/")

    def test_update_enabled(self):
        boot = colony_print.boot.ColonyPrintBoot(environ=dict())
        self.assertEqual(boot.update_enabled, True)

        for value in ("0", "false", "False", "no", " off "):
            boot = colony_print.boot.ColonyPrintBoot(environ=dict(NODE_UPDATE=value))
            self.assertEqual(boot.update_enabled, False)

        for value in ("1", "true", "yes", ""):
            boot = colony_print.boot.ColonyPrintBoot(environ=dict(NODE_UPDATE=value))
            self.assertEqual(boot.update_enabled, True)
