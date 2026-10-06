#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import time
import codecs
import shutil
import logging
import argparse
import tempfile
import importlib
import subprocess

BASE_URL = "https://print.bemisc.com/"
""" The default base URL to be used for the communication with the
Colony Print server, should be the same as the one of the node """

STATE_NAME = "state.env"
""" The name of the state file of the node, kept next to its configuration
file and with its format, that is written by the node (as requested from
the admin) and read by the boot, which never writes the configuration """

PACKAGE = "colony_print"
""" The name of the package of the node, whose modules are loaded before
the update when the boot is run as a module of the package (and not as a
script), so they're unloaded before the node is run, as they may be the
ones of the version that was installed before the update """

PACKAGES = (("colony-print", "NODE_VERSION"), ("npcolony", "NODE_NPCOLONY_VERSION"))
""" The packages of the node that are updated by the boot, together
with the name of the configuration that (optionally) constrains the
version of each of them, every other package is only updated in case
it's required by an updated package """

OPERATORS = ("<", ">", "=", "!", "~")
""" The first characters of the version specifiers (PEP 440), any
other version constraint is considered to be an exact version """

TIMEOUT = 10
""" The timeout (in seconds) of the verification of the package index
that precedes each attempt to update the packages of the node """

RETRIES = 3
""" The number of attempts to update the packages of the node, as the
network may not be ready when the node boots """

RETRY_DELAY = 10.0
""" The delay (in seconds) between the attempts to update the node """

FALSE_VALUES = ("0", "false", "no", "off")
""" The (lower cased) configuration values considered to be false """

LEGACY_VERSION = (3, 6)
""" The first version of the interpreter that is not a legacy one, as
the versions of pip that run on the older ones (eg: Python 2.7, the one
of the Windows XP nodes) are not able to list the versions of a package """


class ColonyPrintBoot(object):
    """
    Boot sequence of the (Windows) nodes, that updates the packages of
    the node from the package index (PyPI by default) and then runs the
    node, being the entry point of the node (Windows) service.

    The node is told that it's run by the boot (through the environment),
    together with the outcome of the update and the path of the state file
    where it keeps the values set from the admin (the auto-update and the
    update forced for the next boot), that are applied over the configuration.

    The module is meant to be run as a script (not imported as part of
    the package) and uses only the standard library until the update is
    done, so that no package that may be updated is loaded (and locked)
    by it, which allows the update of every package (eg: npcolony),
    including the one that contains this file.

    When it's run as a module of the package (python -m colony_print.boot)
    the package is loaded before the update, so its modules are unloaded
    before the node is run, for the node to run only with the updated ones.
    """

    def __init__(
        self,
        environ=None,
        retries=RETRIES,
        retry_delay=RETRY_DELAY,
        legacy=None,
        clean=None,
    ):
        self.environ = os.environ if environ == None else environ
        self.retries = retries
        self.retry_delay = retry_delay
        self.legacy = sys.version_info < LEGACY_VERSION if legacy == None else legacy
        self.clean = __name__ == "__main__" if clean == None else clean

    def main(self, args=None):
        parser = argparse.ArgumentParser(
            description="Updates the packages of the node and runs it"
        )
        parser.add_argument(
            "--config",
            default=self.environ.get("COLONY_PRINT_CONFIG", "config.env"),
            help="path to the (.env like) configuration file of the node",
        )
        parser.add_argument(
            "--no-update", action="store_true", help="skips the update of the node"
        )
        parser.add_argument(
            "--update-only", action="store_true", help="only updates the node"
        )
        args = parser.parse_args(args)

        logging.basicConfig(
            format="%(asctime)s [%(levelname)s] %(message)s", level=logging.DEBUG
        )

        # loads the configuration file of the node into the environment
        # so that it's used by the update and by the node itself, keeping
        # the values the boot was started with, as a node that restarts
        # itself must run the boot once more with only those
        config_path = os.path.abspath(args.config)
        original = dict(self.environ)
        self.apply_config(self.load_config(config_path))
        self.environ["BASE_URL"] = self.base_url

        # keeps the fonts installed on demand next to the configuration file
        # (in the data directory of the node, only accessible to the system
        # and the administrators), unless their path is configured
        if not self.environ.get("FONTS_PATH", None):
            self.environ["FONTS_PATH"] = os.path.join(
                os.path.dirname(config_path), "fonts"
            )

        # applies the state file of the node (kept next to the configuration
        # file) over the configuration, unless the remote control of the node
        # is disabled, notice that a state file that can't be applied only
        # logs a warning and never prevents the node from running
        state_path = os.path.join(os.path.dirname(config_path), STATE_NAME)
        force = False
        if self.control_enabled:
            try:
                force = self.apply_state(state_path)
            except Exception as exception:
                logging.warning(
                    "Problem applying state '%s': %s" % (state_path, str(exception))
                )

        # updates the packages of the node, even with the auto-update disabled
        # when the update is forced (from the admin), notice that a failed
        # update (eg: without internet access) only logs a warning and never
        # prevents the node from running, as the installed packages keep being
        # used until the next (successful) update
        status, error = "skipped", None
        if not args.no_update and (self.update_enabled or force):
            try:
                self.update()
                status = "success"
            except Exception as exception:
                status, error = "failure", str(exception)
                logging.warning(
                    "Problem updating node, running the installed packages: %s" % error
                )

        # hands the marker of the boot, the path of the state file and the
        # outcome of the update over to the node (through the environment),
        # together with the names of the values set by the boot, the ones
        # that are not part of the environment the boot was started with,
        # notice that the node is not told about a boot that skips the update
        # (as told to), as it would not be updated from the admin, being
        # restarted with the same command line
        self.environ["NODE_BOOT"] = "0" if args.no_update else "1"
        self.environ["NODE_STATE_PATH"] = state_path
        self.environ["NODE_UPDATE_STATUS"] = status
        self.environ["NODE_UPDATE_TIME"] = str(time.time())
        self.environ.pop("NODE_UPDATE_ERROR", None)
        if error:
            self.environ["NODE_UPDATE_ERROR"] = error
        # hands the values of the environment the boot was started with
        # that were replaced by it (eg: the auto-update of the state file)
        # over to the node as well, so that they're the ones of the node
        # that restarts itself, as the configuration may change meanwhile
        for key, value in original.items():
            if self.environ.get(key, None) == value:
                continue
            self.environ["NODE_BOOT_VALUE_" + key] = value
        keys = set(self.environ) - set(original)
        self.environ["NODE_BOOT_KEYS"] = ",".join(
            sorted(keys | set(["NODE_BOOT_KEYS"]))
        )

        if args.update_only:
            return
        self.run()

    def run(self):
        # makes sure that the packages installed by the update are
        # found by the import system and then imports and runs the
        # node, using its (possibly new) version
        if hasattr(importlib, "invalidate_caches"):
            importlib.invalidate_caches()

        # unloads the modules of the package that were loaded before the
        # update, when the boot is the program being run (as a module of the
        # package), so that the node doesn't run with the ones of the version
        # that was installed before the update
        if self.clean:
            self.unload(PACKAGE)

        import appier
        import colony_print.node

        # loads the environment into the configuration of appier once more,
        # as it's loaded when appier is imported, which happens before the
        # configuration file is applied when the boot is run as a module of
        # the package (python -m colony_print.boot)
        appier.config.load_env()

        node = colony_print.node.ColonyPrintNode()
        node.loop()

    def unload(self, package):
        """
        Unloads the package with the provided name and its modules (the
        ones that are loaded), so that they're loaded once more, from their
        (possibly updated) files, the next time they're imported.

        :type package: String
        :param package: The name of the package to be unloaded.
        :rtype: List
        :return: The names of the modules that were unloaded.
        """

        names = [
            name
            for name in sys.modules
            if name == package or name.startswith(package + ".")
        ]
        for name in names:
            del sys.modules[name]
        return sorted(names)

    def update(self):
        """
        Updates the packages of the node (colony-print and npcolony) to
        their newest versions in the package index (PyPI by default) or to
        the newest ones allowed by their (optional) version constraints,
        which also allow pinning and rolling back a node, letting pip skip
        the versions that don't support the interpreter (Requires-Python).

        Only the wheels of the packages are installed, so that nothing is
        built (eg: compiled) in the node, and the update is attempted more
        than once, as the network may not be ready when the node boots,
        verifying that the package index is reachable before each attempt,
        as pip keeps the installed packages (exiting with success) when it
        can't reach the index, which would skip the update silently.

        The legacy interpreters (eg: Python 2.7) verify the package index
        by downloading the package of the node, as their versions of pip
        are not able to list the versions of a package (index command).

        :rtype: List
        :return: The requirements that were installed.
        """

        requirements = self.requirements
        index = ["--index-url", self.index_url] if self.index_url else []
        check = [
            sys.executable,
            "-m",
            "pip",
            "index",
            "versions",
            PACKAGES[0][0],
            "--timeout",
            str(TIMEOUT),
            "--retries",
            "1",
            "--disable-pip-version-check",
            "--no-input",
        ] + index
        command = (
            [
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
            + index
            + requirements
        )

        logging.info("Updating packages %s" % ", ".join(requirements))

        # runs pip without any of its configuration files, as its global one
        # (eg: C:\ProgramData\pip\pip.ini) may be created by any user and
        # would make the update (run by the system account) use other packages,
        # notice that pip may still be configured (eg: PIP_PROXY) with values
        # in the configuration of the node, as they're in the environment
        env = dict(self.environ)
        env["PIP_CONFIG_FILE"] = os.devnull

        # downloads the package of the node into a temporary directory to
        # verify the package index in the legacy interpreters, with a try
        # and finally block guaranteeing that the directory is removed
        # regardless of whether the update succeeds or raises
        temp_dir = tempfile.mkdtemp() if self.legacy else None
        if temp_dir:
            check = [
                sys.executable,
                "-m",
                "pip",
                "download",
                PACKAGES[0][0],
                "--no-deps",
                "--only-binary",
                ":all:",
                "--no-cache-dir",
                "--dest",
                temp_dir,
                "--timeout",
                str(TIMEOUT),
                "--retries",
                "1",
                "--disable-pip-version-check",
                "--no-input",
            ] + index

        try:
            retries = max(self.retries, 1)
            for attempt in range(retries):
                code = subprocess.call(check, env=env)
                if code == 0:
                    code = subprocess.call(command, env=env)
                if code == 0:
                    return requirements
                if attempt == retries - 1:
                    break
                logging.warning(
                    "Problem updating packages (code %d), retrying in %.2f seconds"
                    % (code, self.retry_delay)
                )
                time.sleep(self.retry_delay)
            raise RuntimeError("Package update failed with code %d" % code)
        finally:
            if temp_dir:
                shutil.rmtree(temp_dir, ignore_errors=True)

    def requirement(self, name, constraint):
        """
        Builds the requirement (PEP 508) of the package with the provided
        name, constrained by the provided version constraint, which is
        either a version specifier (eg: <0.22, ==0.21.*) or an exact version
        (eg: 0.21.0), an empty constraint allowing any version.

        :type name: String
        :param name: The name of the package.
        :type constraint: String
        :param constraint: The version constraint of the package.
        :rtype: String
        :return: The requirement of the package, to be installed by pip.
        """

        constraint = (constraint or "").strip()
        if not constraint:
            return name
        if not constraint.startswith(OPERATORS):
            constraint = "==" + constraint
        return name + constraint

    def load_config(self, path):
        """
        Loads the (.env like) configuration file in the provided path,
        using the same rules as the loading of the .env files by appier.

        :type path: String
        :param path: The path to the configuration file.
        :rtype: Dictionary
        :return: The configuration values, empty in case the file
        does not exist.
        """

        config = dict()
        if not os.path.exists(path):
            return config

        with open(path, "rb") as file:
            data = file.read()
        if data.startswith(codecs.BOM_UTF8):
            data = data[len(codecs.BOM_UTF8) :]
        data = data.decode("utf-8")

        for line in data.splitlines():
            line = line.strip()
            if not line or line.startswith("#") or not "=" in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if not key:
                continue
            if len(value) > 1 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1].replace('\\"', '"')
            config[key] = value
        return config

    def save_config(self, path, config):
        """
        Saves the provided configuration values in the (.env like) file in
        the provided path, so that they're loaded back by the loading of
        the configuration, the file being replaced atomically (written to
        a temporary file that then takes its place), so that an interrupted
        save never leaves a partial file behind.

        The values are saved as they are (without quotes), which is enough
        for the values of the state file of the node.

        :type path: String
        :param path: The path to the configuration file.
        :type config: Dictionary
        :param config: The configuration values to be saved.
        """

        lines = ["%s=%s" % item for item in sorted(config.items())]
        data = "\r\n".join(lines + [""]).encode("utf-8")

        # replaces the file with the temporary one, with a try and finally
        # block guaranteeing that the temporary file is removed when the save
        # fails, notice that the legacy interpreters (Python 2) are not able
        # to replace a file on windows, where the file is removed first
        temp_path = path + ".tmp"
        try:
            with open(temp_path, "wb") as file:
                file.write(data)
            if os.name == "nt" and not hasattr(os, "replace") and os.path.exists(path):
                os.remove(path)
            getattr(os, "replace", os.rename)(temp_path, path)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def apply_config(self, config, override=False):
        # sets the configuration values in the environment, notice that
        # the values that are already defined in the environment take
        # precedence (unless they're overridden), as in the configuration
        # loading of appier, and that the strings are encoded (as UTF-8) in
        # the interpreters whose environment only accepts byte strings
        # (Python 2), which refuses the values that are not ASCII otherwise
        # (eg: the name of the node)
        for key, value in config.items():
            if not isinstance(key, str):
                key = key.encode("utf-8")
            if not isinstance(value, str):
                value = value.encode("utf-8")
            if key in self.environ and not override:
                continue
            self.environ[key] = value

    def apply_state(self, path):
        """
        Applies the state file of the node in the provided path, the one
        written by the node (as requested from the admin), over the
        configuration: the auto-update of the node (NODE_UPDATE), that takes
        precedence over the one of the configuration, and the update forced
        for a single boot (NODE_UPDATE_ONCE), that is removed from the file
        (consumed) before the update runs, so that only this boot is forced.

        :type path: String
        :param path: The path to the state file.
        :rtype: bool
        :return: If the update of the packages is forced for this boot,
        even with the auto-update disabled.
        """

        state = self.load_config(path)
        if "NODE_UPDATE" in state:
            self.apply_config(dict(NODE_UPDATE=state["NODE_UPDATE"]), override=True)
        if not "NODE_UPDATE_ONCE" in state:
            return False
        value = state.pop("NODE_UPDATE_ONCE")
        self.save_config(path, state)
        return not value.strip().lower() in FALSE_VALUES

    @property
    def requirements(self):
        return [
            self.requirement(name, self.environ.get(key, None))
            for name, key in PACKAGES
        ]

    @property
    def base_url(self):
        base_url = self.environ.get("BASE_URL", None) or BASE_URL
        if not base_url.endswith("/"):
            base_url += "/"
        return base_url

    @property
    def index_url(self):
        return self.environ.get("NODE_INDEX_URL", "").strip() or None

    @property
    def update_enabled(self):
        value = self.environ.get("NODE_UPDATE", "1")
        return not value.strip().lower() in FALSE_VALUES

    @property
    def control_enabled(self):
        value = self.environ.get("NODE_CONTROL", "1")
        return not value.strip().lower() in FALSE_VALUES


if __name__ == "__main__":
    boot = ColonyPrintBoot()
    boot.main()
else:
    __path__ = []
