#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import time
import codecs
import logging
import argparse
import importlib
import subprocess

BASE_URL = "https://print.bemisc.com/"
""" The default base URL to be used for the communication with the
Colony Print server, should be the same as the one of the node """

PACKAGES = (("colony-print", "NODE_VERSION"), ("npcolony", "NODE_NPCOLONY_VERSION"))
""" The packages of the node that are updated by the boot, together
with the name of the configuration that (optionally) constrains the
version of each of them, every other package is only updated in case
it's required by an updated package """

OPERATORS = ("<", ">", "=", "!", "~")
""" The first characters of the version specifiers (PEP 440), any
other version constraint is considered to be an exact version """

RETRIES = 3
""" The number of attempts to update the packages of the node, as the
network may not be ready when the node boots """

RETRY_DELAY = 10.0
""" The delay (in seconds) between the attempts to update the node """

FALSE_VALUES = ("0", "false", "no", "off")
""" The (lower cased) configuration values considered to be false """


class ColonyPrintBoot(object):
    """
    Boot sequence of the (Windows) nodes, that updates the packages of
    the node from the package index (PyPI by default) and then runs the
    node, being the entry point of the node (Windows) service.

    The module is meant to be run as a script (not imported as part of
    the package) and uses only the standard library until the update is
    done, so that no package that may be updated is loaded (and locked)
    by it, which allows the update of every package (eg: npcolony),
    including the one that contains this file.
    """

    def __init__(self, environ=None, retries=RETRIES, retry_delay=RETRY_DELAY):
        self.environ = os.environ if environ == None else environ
        self.retries = retries
        self.retry_delay = retry_delay

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
        # so that it's used by the update and by the node itself
        config_path = os.path.abspath(args.config)
        self.apply_config(self.load_config(config_path))
        self.environ["BASE_URL"] = self.base_url

        # updates the packages of the node, notice that a failed update (eg:
        # without internet access) only logs a warning and never prevents the
        # node from running, as the installed packages keep being used until
        # the next (successful) update
        if not args.no_update and self.update_enabled:
            try:
                self.update()
            except Exception as exception:
                logging.warning(
                    "Problem updating node, running the installed packages: %s"
                    % str(exception)
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

        import colony_print.node

        node = colony_print.node.ColonyPrintNode()
        node.loop()

    def update(self):
        """
        Updates the packages of the node (colony-print and npcolony) to
        their newest versions in the package index (PyPI by default) or to
        the newest ones allowed by their (optional) version constraints,
        which also allow pinning and rolling back a node, letting pip skip
        the versions that don't support the interpreter (Requires-Python).

        Only the wheels of the packages are installed, so that nothing is
        built (eg: compiled) in the node, and the update is attempted more
        than once, as the network may not be ready when the node boots.

        :rtype: List
        :return: The requirements that were installed.
        """

        requirements = self.requirements
        command = [
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
        if self.index_url:
            command += ["--index-url", self.index_url]
        command += requirements

        logging.info("Updating packages %s" % ", ".join(requirements))
        retries = max(self.retries, 1)
        for attempt in range(retries):
            code = subprocess.call(command)
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

    def apply_config(self, config):
        # sets the configuration values in the environment, notice that
        # the values that are already defined in the environment take
        # precedence, as in the configuration loading of appier
        for key, value in config.items():
            if key in self.environ:
                continue
            self.environ[key] = value

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


if __name__ == "__main__":
    boot = ColonyPrintBoot()
    boot.main()
else:
    __path__ = []
