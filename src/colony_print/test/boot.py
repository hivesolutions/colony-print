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

DOWNLOAD_COMMAND = [
    sys.executable,
    "-m",
    "pip",
    "download",
    "colony-print",
    "--no-deps",
    "--only-binary",
    ":all:",
    "--no-cache-dir",
    "--dest",
]
""" The command (without the temporary directory and the options that
follow it) that is expected to be run by the boot of a legacy interpreter
to verify that the package index is reachable """

DOWNLOAD_OPTIONS = [
    "--timeout",
    "10",
    "--retries",
    "1",
    "--disable-pip-version-check",
    "--no-input",
]
""" The options that are expected to follow the temporary directory in
the command run by the boot of a legacy interpreter """


class MockSubprocess(object):
    """
    Stand-in for the subprocess module that records the commands that
    are called (and their environments) and returns the configured exit
    codes (one for each call, the last one being kept) or raises the
    configured error, so that the update of the packages can be exercised
    without pip.

    The existence of the directory of each download (the one of the
    legacy interpreters) is also recorded, as pip downloads to it.
    """

    codes = [0]
    error = None
    calls = []
    envs = []
    dests = []

    @staticmethod
    def call(command, env=None):
        MockSubprocess.calls.append(command)
        MockSubprocess.envs.append(env)
        if "--dest" in command:
            dest = command[command.index("--dest") + 1]
            MockSubprocess.dests.append(os.path.isdir(dest))
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
            environ=self.environ, retry_delay=0.0, legacy=False
        )
        self.temp_path = tempfile.mkdtemp(prefix="colony-print-boot-test-")
        self.config_path = os.path.join(self.temp_path, "config.env")
        MockSubprocess.codes = [0]
        MockSubprocess.error = None
        MockSubprocess.calls = []
        MockSubprocess.envs = []
        MockSubprocess.dests = []
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

    def _temp_dir(self, command):
        return command[command.index("--dest") + 1]

    def test_main(self):
        self._write(
            self.config_path,
            b"BASE_URL=https://print.example.com\r\n"
            + b"SECRET_KEY=secret\r\n"
            + b"NODE_VERSION=0.21.0\r\n",
        )
        environ = dict()
        boot = colony_print.boot.ColonyPrintBoot(
            environ=environ, retry_delay=0.0, legacy=False
        )

        boot.main(["--config", self.config_path])
        self.assertEqual(environ["BASE_URL"], "https://print.example.com/")
        self.assertEqual(environ["SECRET_KEY"], "secret")
        self.assertEqual(
            environ["FONTS_PATH"],
            os.path.join(os.path.dirname(os.path.abspath(self.config_path)), "fonts"),
        )
        self.assertEqual(
            MockSubprocess.calls,
            [INDEX_COMMAND, PIP_COMMAND + ["colony-print==0.21.0", "npcolony"]],
        )
        self.assertEqual(MockColonyPrintNode.loops, 1)

        # the node is told that it's run by the boot, together with the path
        # of its state file (next to the configuration file), the outcome of
        # the update and the names of the values that were set by the boot
        self.assertEqual(environ["NODE_BOOT"], "1")
        self.assertEqual(
            environ["NODE_STATE_PATH"],
            os.path.join(
                os.path.dirname(os.path.abspath(self.config_path)), "state.env"
            ),
        )
        self.assertEqual(environ["NODE_UPDATE_STATUS"], "success")
        self.assertEqual(float(environ["NODE_UPDATE_TIME"]) > 0.0, True)
        self.assertEqual("NODE_UPDATE_ERROR" in environ, False)
        self.assertEqual(environ["NODE_BOOT_KEYS"].split(","), sorted(environ.keys()))
        for value in environ.values():
            self.assertEqual(type(value), str)

    def test_main_boot_keys(self):
        # only the values set by the boot (the ones of the configuration file
        # and the ones handed over to the node) are named, the ones that were
        # replaced by it (eg: by the state file) being handed over with their
        # original values, so that removing the first ones and restoring the
        # other ones results in the environment the boot was started with
        self._write(
            self.config_path,
            b"BASE_URL=https://other.example.com/\r\n"
            + b"SECRET_KEY=secret\r\n"
            + b"NODE_NAME=Shop\r\n",
        )
        self._write(os.path.join(self.temp_path, "state.env"), b"NODE_UPDATE=0\r\n")
        original = dict(
            BASE_URL="https://print.example.com",
            NODE_UPDATE="1",
            NODE_UPDATE_ERROR="Package update failed with code 1",
            PATH="/usr/bin",
        )
        environ = dict(original)
        boot = colony_print.boot.ColonyPrintBoot(environ=environ, retry_delay=0.0)

        boot.main(["--config", self.config_path])
        self.assertEqual(environ["BASE_URL"], "https://print.example.com/")
        self.assertEqual(environ["NODE_UPDATE"], "0")
        keys = environ["NODE_BOOT_KEYS"].split(",")
        self.assertEqual(
            keys,
            [
                "FONTS_PATH",
                "NODE_BOOT",
                "NODE_BOOT_KEYS",
                "NODE_BOOT_VALUE_BASE_URL",
                "NODE_BOOT_VALUE_NODE_UPDATE",
                "NODE_BOOT_VALUE_NODE_UPDATE_ERROR",
                "NODE_NAME",
                "NODE_STATE_PATH",
                "NODE_UPDATE_STATUS",
                "NODE_UPDATE_TIME",
                "SECRET_KEY",
            ],
        )
        self.assertEqual(
            sorted(key for key in environ if not key in keys),
            ["BASE_URL", "NODE_UPDATE", "PATH"],
        )
        self.assertEqual(
            environ["NODE_BOOT_VALUE_BASE_URL"], "https://print.example.com"
        )
        self.assertEqual(environ["NODE_BOOT_VALUE_NODE_UPDATE"], "1")
        self.assertEqual(
            environ["NODE_BOOT_VALUE_NODE_UPDATE_ERROR"],
            "Package update failed with code 1",
        )
        self.assertEqual("NODE_BOOT_VALUE_PATH" in environ, False)
        restarted = dict((key, environ[key]) for key in environ if not key in keys)
        restarted.update(
            (key[len("NODE_BOOT_VALUE_") :], environ[key])
            for key in keys
            if key.startswith("NODE_BOOT_VALUE_")
        )
        self.assertEqual(restarted, original)

        # the error of the update of a previous boot is not kept when the
        # update doesn't fail, even if it's part of the environment
        self.assertEqual(environ["NODE_UPDATE_STATUS"], "skipped")
        self.assertEqual("NODE_UPDATE_ERROR" in environ, False)

        # the names handed over by a previous boot are not part of the
        # environment the boot was started with, so they're named once more
        environ = dict(PATH="/usr/bin", NODE_BOOT_KEYS="NODE_BOOT,NODE_BOOT_KEYS")
        boot = colony_print.boot.ColonyPrintBoot(environ=environ, retry_delay=0.0)
        boot.main(["--config", self.config_path, "--no-update"])
        keys = environ["NODE_BOOT_KEYS"].split(",")
        self.assertEqual("NODE_BOOT_KEYS" in keys, True)
        self.assertEqual(keys.count("NODE_BOOT_KEYS"), 1)
        self.assertEqual(sorted(key for key in environ if not key in keys), ["PATH"])

        # no value is handed over when the boot replaces none, as with a
        # node whose configuration is only the one of its file
        self.assertEqual([key for key in keys if "NODE_BOOT_VALUE_" in key], [])
        for value in environ.values():
            self.assertEqual(type(value), str)

    def test_main_config_default(self):
        self._write(self.config_path, b"NODE_UPDATE=0\r\nNODE_NAME=Shop\r\n")
        environ = dict(COLONY_PRINT_CONFIG=self.config_path)
        boot = colony_print.boot.ColonyPrintBoot(environ=environ, retry_delay=0.0)

        boot.main([])
        self.assertEqual(environ["NODE_NAME"], "Shop")
        self.assertEqual(environ["BASE_URL"], colony_print.boot.BASE_URL)
        self.assertEqual(environ["FONTS_PATH"].endswith("fonts"), True)

        self.assertEqual(MockSubprocess.calls, [])
        self.assertEqual(MockColonyPrintNode.loops, 1)

    def test_main_fonts_path(self):
        # the path of the fonts given in the configuration (or in the
        # environment) is kept as it is, instead of the data directory
        self._write(self.config_path, b"NODE_UPDATE=0\r\nFONTS_PATH=D:\\fonts\r\n")
        environ = dict(COLONY_PRINT_CONFIG=self.config_path)
        boot = colony_print.boot.ColonyPrintBoot(environ=environ, retry_delay=0.0)
        boot.main([])
        self.assertEqual(environ["FONTS_PATH"], "D:\\fonts")

        environ = dict(COLONY_PRINT_CONFIG=self.config_path, FONTS_PATH="E:\\fonts")
        boot = colony_print.boot.ColonyPrintBoot(environ=environ, retry_delay=0.0)
        boot.main([])
        self.assertEqual(environ["FONTS_PATH"], "E:\\fonts")

    def test_main_config_missing(self):
        self.boot.main(["--config", self.config_path, "--no-update"])
        self.assertEqual(self.environ["BASE_URL"], "https://print.example.com/")
        self.assertEqual(MockColonyPrintNode.loops, 1)

    def test_main_no_update(self):
        self.boot.main(["--config", self.config_path, "--no-update"])
        self.assertEqual(MockSubprocess.calls, [])
        self.assertEqual(MockColonyPrintNode.loops, 1)

        # the node is not told about the boot that skips the update (as told
        # to), as it would never be updated from the admin, the other values
        # being handed over to it (eg: for it to restart)
        self.assertEqual(self.environ["NODE_BOOT"], "0")
        self.assertEqual(self.environ["NODE_UPDATE_STATUS"], "skipped")
        self.assertEqual("NODE_BOOT" in self.environ["NODE_BOOT_KEYS"].split(","), True)

        # the same environment is the one of a boot that updates once the
        # boot is no longer told to skip the update
        self.boot.main(["--config", self.config_path])
        self.assertEqual(self.environ["NODE_BOOT"], "1")
        self.assertEqual(self.environ["NODE_UPDATE_STATUS"], "success")

    def test_main_update_only(self):
        self.boot.main(["--config", self.config_path, "--update-only"])
        self.assertEqual(self._requirements(), [["colony-print", "npcolony"]])
        self.assertEqual(MockColonyPrintNode.loops, 0)

    def test_main_update_disabled(self):
        self._write(self.config_path, b"NODE_UPDATE=false\r\n")
        self.boot.main(["--config", self.config_path])
        self.assertEqual(MockSubprocess.calls, [])
        self.assertEqual(MockColonyPrintNode.loops, 1)
        self.assertEqual(self.environ["NODE_UPDATE_STATUS"], "skipped")
        self.assertEqual("NODE_UPDATE_ERROR" in self.environ, False)

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

            # the failure of the update is handed over to the node (that
            # reports it), which is still run by the boot
            self.assertEqual(self.environ["NODE_UPDATE_STATUS"], "failure")
            self.assertEqual(
                self.environ["NODE_UPDATE_ERROR"], "Package update failed with code 1"
            )
            self.assertEqual(
                "NODE_UPDATE_ERROR" in self.environ["NODE_BOOT_KEYS"].split(","), True
            )

            MockSubprocess.calls = []
            MockSubprocess.error = OSError("No such file or directory")
            self.boot.main(["--config", self.config_path])
            self.assertEqual(len(MockSubprocess.calls), 1)
            self.assertEqual(MockColonyPrintNode.loops, 2)
            self.assertEqual(self.environ["NODE_UPDATE_STATUS"], "failure")
            self.assertEqual(
                self.environ["NODE_UPDATE_ERROR"], "No such file or directory"
            )

            # the error is no longer handed over once the update succeeds
            MockSubprocess.error = None
            MockSubprocess.codes = [0]
            self.boot.main(["--config", self.config_path])
            self.assertEqual(MockColonyPrintNode.loops, 3)
            self.assertEqual(self.environ["NODE_UPDATE_STATUS"], "success")
            self.assertEqual("NODE_UPDATE_ERROR" in self.environ, False)
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

    def test_main_state(self):
        # the state file of the node (next to the configuration file) holds
        # the auto-update set from the admin, that takes precedence over the
        # one of the configuration (and of the environment)
        state_path = os.path.join(self.temp_path, "state.env")
        self._write(self.config_path, b"NODE_UPDATE=1\r\n")
        self._write(state_path, b"NODE_UPDATE=0\r\n")
        self.boot.main(["--config", self.config_path])
        self.assertEqual(self.environ["NODE_UPDATE"], "0")
        self.assertEqual(self.environ["NODE_UPDATE_STATUS"], "skipped")
        self.assertEqual(MockSubprocess.calls, [])
        self.assertEqual(MockColonyPrintNode.loops, 1)
        self.assertEqual(self.boot.load_config(state_path), dict(NODE_UPDATE="0"))

        self._write(state_path, b"NODE_UPDATE=1\r\n")
        self.boot.main(["--config", self.config_path])
        self.assertEqual(self.environ["NODE_UPDATE"], "1")
        self.assertEqual(self.environ["NODE_UPDATE_STATUS"], "success")
        self.assertEqual(self._requirements(), [["colony-print", "npcolony"]])

        # the update forced from the admin runs even with the auto-update
        # disabled, but only once, as it's removed from the state file (that
        # keeps its other values) before the update runs
        self._write(state_path, b"NODE_UPDATE=0\r\nNODE_UPDATE_ONCE=1\r\n")
        MockSubprocess.calls = []
        self.boot.main(["--config", self.config_path])
        self.assertEqual(self.environ["NODE_UPDATE"], "0")
        self.assertEqual(self.environ["NODE_UPDATE_STATUS"], "success")
        self.assertEqual("NODE_UPDATE_ONCE" in self.environ, False)
        self.assertEqual(self._requirements(), [["colony-print", "npcolony"]])
        self.assertEqual(self.boot.load_config(state_path), dict(NODE_UPDATE="0"))

        MockSubprocess.calls = []
        self.boot.main(["--config", self.config_path])
        self.assertEqual(self.environ["NODE_UPDATE_STATUS"], "skipped")
        self.assertEqual(MockSubprocess.calls, [])
        self.assertEqual(MockColonyPrintNode.loops, 4)

        # a forced update that fails is also consumed and handed over to
        # the node as a failure, the node being run anyway
        self._write(state_path, b"NODE_UPDATE=0\r\nNODE_UPDATE_ONCE=1\r\n")
        MockSubprocess.codes = [1]
        self.boot.main(["--config", self.config_path])
        self.assertEqual(self.environ["NODE_UPDATE_STATUS"], "failure")
        self.assertEqual(
            self.environ["NODE_UPDATE_ERROR"], "Package update failed with code 1"
        )
        self.assertEqual(self.boot.load_config(state_path), dict(NODE_UPDATE="0"))
        self.assertEqual(MockColonyPrintNode.loops, 5)

        # the update is not forced when the boot is told to skip it, the
        # forced update being consumed anyway
        self._write(state_path, b"NODE_UPDATE_ONCE=1\r\n")
        MockSubprocess.codes = [0]
        MockSubprocess.calls = []
        self.boot.main(["--config", self.config_path, "--no-update"])
        self.assertEqual(self.environ["NODE_UPDATE_STATUS"], "skipped")
        self.assertEqual(MockSubprocess.calls, [])
        self.assertEqual(self.boot.load_config(state_path), dict())

    def test_main_state_error(self):
        # a state file that can't be loaded (a directory in its place) only
        # logs a warning, the node being updated and run as without it
        state_path = os.path.join(self.temp_path, "state.env")
        os.makedirs(state_path)
        handler = MockLoggingHandler()
        logger = logging.getLogger()
        level = logger.level
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        try:
            self.boot.main(["--config", self.config_path])
            self.assertEqual(self._requirements(), [["colony-print", "npcolony"]])
            self.assertEqual(self.environ["NODE_UPDATE_STATUS"], "success")
            self.assertEqual(MockColonyPrintNode.loops, 1)
            shutil.rmtree(state_path)

            # a forced update that can't be consumed (the state file can't be
            # saved) is not run, as it would be run by every boot, the
            # auto-update of the state file being applied anyway
            self._write(state_path, b"NODE_UPDATE=0\r\nNODE_UPDATE_ONCE=1\r\n")
            os.makedirs(state_path + ".tmp")
            MockSubprocess.calls = []
            self.boot.main(["--config", self.config_path])
            self.assertEqual(MockSubprocess.calls, [])
            self.assertEqual(self.environ["NODE_UPDATE"], "0")
            self.assertEqual(self.environ["NODE_UPDATE_STATUS"], "skipped")
            self.assertEqual(MockColonyPrintNode.loops, 2)
        finally:
            logger.removeHandler(handler)
            logger.setLevel(level)

        problems = [
            record
            for record in handler.records
            if "Problem applying state" in record.getMessage()
        ]
        self.assertEqual(len(problems), 2)
        self.assertEqual([record.levelno for record in problems], [logging.WARNING] * 2)
        self.assertEqual(state_path in problems[0].getMessage(), True)

    def test_main_control_disabled(self):
        # the state file is ignored (and left untouched) when the remote
        # control of the node is disabled in its configuration, which can't
        # be changed from the admin, the node being told about the boot anyway
        state_path = os.path.join(self.temp_path, "state.env")
        self._write(self.config_path, b"NODE_CONTROL=0\r\nNODE_UPDATE=0\r\n")
        self._write(state_path, b"NODE_UPDATE=1\r\nNODE_UPDATE_ONCE=1\r\n")
        self.boot.main(["--config", self.config_path])
        self.assertEqual(MockSubprocess.calls, [])
        self.assertEqual(self.environ["NODE_UPDATE"], "0")
        self.assertEqual(self.environ["NODE_CONTROL"], "0")
        self.assertEqual(self.environ["NODE_BOOT"], "1")
        self.assertEqual(self.environ["NODE_STATE_PATH"], state_path)
        self.assertEqual(self.environ["NODE_UPDATE_STATUS"], "skipped")
        self.assertEqual(
            self.boot.load_config(state_path),
            dict(NODE_UPDATE="1", NODE_UPDATE_ONCE="1"),
        )
        self.assertEqual(MockColonyPrintNode.loops, 1)

    def test_run(self):
        self.boot.run()
        self.assertEqual(MockColonyPrintNode.loops, 1)

        # the values set in the environment after appier is imported (as the
        # ones of the configuration file, when the boot is run as a module of
        # the package) are part of the configuration of the node
        os.environ["COLONY_PRINT_BOOT_TEST"] = "value"
        try:
            self.assertEqual(appier.conf("COLONY_PRINT_BOOT_TEST", None), None)
            self.boot.run()
            self.assertEqual(appier.conf("COLONY_PRINT_BOOT_TEST", None), "value")
        finally:
            del os.environ["COLONY_PRINT_BOOT_TEST"]
            appier.conf_r("COLONY_PRINT_BOOT_TEST")
        self.assertEqual(MockColonyPrintNode.loops, 2)

        # the modules of the package are only unloaded (before the node is
        # run) when the boot is the program being run, as they're loaded
        # before the update when it's run as a module of the package, the
        # ones of the program that imports the boot being kept
        self.assertEqual(self.boot.clean, False)
        self.assertEqual(colony_print.boot.ColonyPrintBoot(environ=dict()).clean, False)
        package = colony_print.boot.PACKAGE
        colony_print.boot.PACKAGE = "colony_print_boot_test"
        sys.modules["colony_print_boot_test"] = colony_print
        sys.modules["colony_print_boot_test.node"] = colony_print.node
        try:
            self.boot.run()
            self.assertEqual("colony_print_boot_test" in sys.modules, True)
            self.assertEqual("colony_print_boot_test.node" in sys.modules, True)

            boot = colony_print.boot.ColonyPrintBoot(environ=dict(), clean=True)
            self.assertEqual(boot.clean, True)
            boot.run()
            self.assertEqual("colony_print_boot_test" in sys.modules, False)
            self.assertEqual("colony_print_boot_test.node" in sys.modules, False)
        finally:
            colony_print.boot.PACKAGE = package
            sys.modules.pop("colony_print_boot_test", None)
            sys.modules.pop("colony_print_boot_test.node", None)
        self.assertEqual(MockColonyPrintNode.loops, 4)
        self.assertEqual(sys.modules["colony_print.node"] is colony_print.node, True)

    def test_unload(self):
        # only the package and its modules are unloaded, the packages that
        # share its prefix (and every other module) being kept
        names = (
            "colony_print_boot_test",
            "colony_print_boot_test.node",
            "colony_print_boot_test.printing.pdf",
            "colony_print_boot_tests",
            "colony_print_boot_tests.node",
        )
        for name in names:
            sys.modules[name] = colony_print
        try:
            self.assertEqual(
                self.boot.unload("colony_print_boot_test"),
                [
                    "colony_print_boot_test",
                    "colony_print_boot_test.node",
                    "colony_print_boot_test.printing.pdf",
                ],
            )
            self.assertEqual(
                sorted(name for name in names if name in sys.modules),
                ["colony_print_boot_tests", "colony_print_boot_tests.node"],
            )
            self.assertEqual("colony_print.boot" in sys.modules, True)

            # a package that is not loaded has nothing to be unloaded
            self.assertEqual(self.boot.unload("colony_print_boot_test"), [])
            self.assertEqual(self.boot.unload("colony_print_boot_test.node"), [])
        finally:
            for name in names:
                sys.modules.pop(name, None)

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

    def test_update_legacy(self):
        # the interpreters older than the first one that is not a legacy
        # one are the legacy ones, unless the boot is told otherwise
        boot = colony_print.boot.ColonyPrintBoot(environ=self.environ)
        self.assertEqual(
            boot.legacy, sys.version_info < colony_print.boot.LEGACY_VERSION
        )
        self.assertEqual(self.boot.legacy, False)

        # the legacy interpreters verify the package index by downloading the
        # package of the node (as their pip has no index command) into a
        # temporary directory, that exists while pip runs and is removed once
        # the update is done, running pip without its configuration files
        boot = colony_print.boot.ColonyPrintBoot(
            environ=self.environ, retry_delay=0.0, legacy=True
        )
        self.assertEqual(boot.update(), ["colony-print", "npcolony"])
        temp_dir = self._temp_dir(MockSubprocess.calls[0])
        self.assertEqual(
            MockSubprocess.calls,
            [
                DOWNLOAD_COMMAND + [temp_dir] + DOWNLOAD_OPTIONS,
                PIP_COMMAND + ["colony-print", "npcolony"],
            ],
        )
        self.assertEqual(os.path.isabs(temp_dir), True)
        self.assertEqual(MockSubprocess.dests, [True])
        self.assertEqual(os.path.exists(temp_dir), False)
        for env in MockSubprocess.envs:
            self.assertEqual(env["PIP_CONFIG_FILE"], os.devnull)

        # the package is downloaded from the custom index, when defined, and
        # without the constraint of its version, as only the index is verified
        self.environ.update(
            NODE_VERSION="0.20.0", NODE_INDEX_URL="https://pypi.example.com/simple/"
        )
        MockSubprocess.calls = []
        self.assertEqual(boot.update(), ["colony-print==0.20.0", "npcolony"])
        temp_dir = self._temp_dir(MockSubprocess.calls[0])
        self.assertEqual(
            MockSubprocess.calls,
            [
                DOWNLOAD_COMMAND
                + [temp_dir]
                + DOWNLOAD_OPTIONS
                + ["--index-url", "https://pypi.example.com/simple/"],
                PIP_COMMAND
                + ["--index-url", "https://pypi.example.com/simple/"]
                + ["colony-print==0.20.0", "npcolony"],
            ],
        )
        self.assertEqual(os.path.exists(temp_dir), False)
        del self.environ["NODE_VERSION"]
        del self.environ["NODE_INDEX_URL"]

        # every attempt downloads to the same directory, that is also removed
        # when the update fails, without trying to install the packages when
        # the index is not reachable
        MockSubprocess.codes = [1]
        MockSubprocess.calls = []
        MockSubprocess.dests = []
        with self.assertRaises(RuntimeError) as context:
            boot.update()
        self.assertEqual(str(context.exception), "Package update failed with code 1")
        temp_dir = self._temp_dir(MockSubprocess.calls[0])
        self.assertEqual(
            MockSubprocess.calls,
            [DOWNLOAD_COMMAND + [temp_dir] + DOWNLOAD_OPTIONS]
            * colony_print.boot.RETRIES,
        )
        self.assertEqual(MockSubprocess.dests, [True] * colony_print.boot.RETRIES)
        self.assertEqual(os.path.exists(temp_dir), False)

        # the directory is removed even when pip is not able to run
        MockSubprocess.calls = []
        MockSubprocess.error = OSError("No such file or directory")
        self.assertRaises(OSError, boot.update)
        self.assertEqual(len(MockSubprocess.calls), 1)
        self.assertEqual(os.path.exists(self._temp_dir(MockSubprocess.calls[0])), False)

        # no directory is created by the interpreters that are not legacy
        MockSubprocess.error = None
        MockSubprocess.codes = [0]
        MockSubprocess.calls = []
        MockSubprocess.dests = []
        self.boot.update()
        self.assertEqual(MockSubprocess.calls[0], INDEX_COMMAND)
        self.assertEqual(MockSubprocess.dests, [])

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

    def test_save_config(self):
        # the values are saved one by line (sorted by name), so that they're
        # loaded back as they were, leaving no temporary file behind
        config = dict(NODE_UPDATE="0", NODE_UPDATE_ONCE="1")
        self.boot.save_config(self.config_path, config)
        with open(self.config_path, "rb") as file:
            data = file.read()
        self.assertEqual(data, b"NODE_UPDATE=0\r\nNODE_UPDATE_ONCE=1\r\n")
        self.assertEqual(self.boot.load_config(self.config_path), config)
        self.assertEqual(os.listdir(self.temp_path), ["config.env"])

        # an existing file is replaced, the values that are not ASCII being
        # saved as UTF-8 (the encoding of the configuration)
        label = appier.legacy.u("São João")
        self.boot.save_config(self.config_path, dict(NODE_LABEL=label))
        self.assertEqual(
            self.boot.load_config(self.config_path), dict(NODE_LABEL=label)
        )
        self.boot.save_config(self.config_path, dict())
        self.assertEqual(self.boot.load_config(self.config_path), dict())
        with open(self.config_path, "rb") as file:
            self.assertEqual(file.read(), b"")

        # a save that fails (a directory in the place of the file) leaves no
        # temporary file behind and keeps the directory as it was
        path = os.path.join(self.temp_path, "state.env")
        os.makedirs(path)
        self.assertRaises(Exception, lambda: self.boot.save_config(path, config))
        self.assertEqual(os.path.isdir(path), True)
        self.assertEqual(
            sorted(os.listdir(self.temp_path)), ["config.env", "state.env"]
        )

        # a temporary file that can't be written (no directory) keeps the
        # file as it was, as it's only replaced once the values are written
        path = os.path.join(self.temp_path, "missing", "state.env")
        self.assertRaises(IOError, lambda: self.boot.save_config(path, config))
        self.assertEqual(os.path.exists(os.path.dirname(path)), False)

    def test_apply_config(self):
        environ = dict(BASE_URL="https://other.example.com/")
        boot = colony_print.boot.ColonyPrintBoot(environ=environ)
        boot.apply_config(dict(BASE_URL="https://print.example.com/", SECRET_KEY="key"))
        self.assertEqual(
            environ, dict(BASE_URL="https://other.example.com/", SECRET_KEY="key")
        )

        # the values that are defined in the environment are only replaced
        # when the configuration overrides them (as the state of the node)
        boot.apply_config(dict(BASE_URL="https://print.example.com/"), override=True)
        self.assertEqual(
            environ, dict(BASE_URL="https://print.example.com/", SECRET_KEY="key")
        )
        boot.apply_config(dict(BASE_URL="https://other.example.com/"), override=True)

        # the values loaded from the configuration file (unicode strings) are
        # set as the strings of the environment, which are byte strings (so
        # encoded as UTF-8) in Python 2, as its environment refuses the unicode
        # strings that are not ASCII (eg: the name of the node)
        label = appier.legacy.u("São João")
        boot.apply_config(
            {
                appier.legacy.u("BASE_URL"): appier.legacy.u("https://example.com/"),
                appier.legacy.u("NODE_LABEL"): label,
            }
        )
        self.assertEqual(environ["BASE_URL"], "https://other.example.com/")
        self.assertEqual(
            environ["NODE_LABEL"],
            label if appier.legacy.PYTHON_3 else label.encode("utf-8"),
        )
        for key, value in environ.items():
            self.assertEqual(type(key), str)
            self.assertEqual(type(value), str)

    def test_apply_state(self):
        # a node without a state file has nothing applied (nor created)
        state_path = os.path.join(self.temp_path, "state.env")
        self.assertEqual(self.boot.apply_state(state_path), False)
        self.assertEqual("NODE_UPDATE" in self.environ, False)
        self.assertEqual(os.path.exists(state_path), False)

        # the auto-update of the state file is set in the environment, even
        # when it's already defined in it, leaving the state file untouched
        self._write(state_path, b"# state\r\nNODE_UPDATE=0\r\n")
        self.assertEqual(self.boot.apply_state(state_path), False)
        self.assertEqual(self.environ["NODE_UPDATE"], "0")
        self.assertEqual(self.boot.update_enabled, False)
        with open(state_path, "rb") as file:
            self.assertEqual(file.read(), b"# state\r\nNODE_UPDATE=0\r\n")

        self._write(state_path, b"NODE_UPDATE=yes\r\n")
        self.assertEqual(self.boot.apply_state(state_path), False)
        self.assertEqual(self.environ["NODE_UPDATE"], "yes")
        self.assertEqual(self.boot.update_enabled, True)

        # the forced update is removed from the state file, that keeps its
        # other values, and is never set in the environment
        self._write(
            state_path, b"NODE_UPDATE=0\r\nNODE_UPDATE_ONCE=1\r\nOTHER=value\r\n"
        )
        self.assertEqual(self.boot.apply_state(state_path), True)
        self.assertEqual(self.environ["NODE_UPDATE"], "0")
        self.assertEqual("NODE_UPDATE_ONCE" in self.environ, False)
        self.assertEqual("OTHER" in self.environ, False)
        self.assertEqual(
            self.boot.load_config(state_path), dict(NODE_UPDATE="0", OTHER="value")
        )
        self.assertEqual(self.boot.apply_state(state_path), False)

        # a forced update with a false value doesn't force the update, but
        # is removed from the state file as any other
        for value in (b"0", b"false", b" Off "):
            self._write(state_path, b"NODE_UPDATE_ONCE=" + value + b"\r\n")
            self.assertEqual(self.boot.apply_state(state_path), False)
            self.assertEqual(self.boot.load_config(state_path), dict())
        for value in (b"1", b"true", b""):
            self._write(state_path, b"NODE_UPDATE_ONCE=" + value + b"\r\n")
            self.assertEqual(self.boot.apply_state(state_path), True)
            self.assertEqual(self.boot.load_config(state_path), dict())

        # the values of the state file (unicode strings) are set as the
        # strings of the environment, as the ones of the configuration
        self._write(state_path, b"NODE_UPDATE=1\r\n")
        self.boot.apply_state(state_path)
        self.assertEqual(type(self.environ["NODE_UPDATE"]), str)

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

    def test_control_enabled(self):
        boot = colony_print.boot.ColonyPrintBoot(environ=dict())
        self.assertEqual(boot.control_enabled, True)

        for value in ("0", "false", "False", "no", " off "):
            boot = colony_print.boot.ColonyPrintBoot(environ=dict(NODE_CONTROL=value))
            self.assertEqual(boot.control_enabled, False)

        for value in ("1", "true", "yes", ""):
            boot = colony_print.boot.ColonyPrintBoot(environ=dict(NODE_CONTROL=value))
            self.assertEqual(boot.control_enabled, True)
