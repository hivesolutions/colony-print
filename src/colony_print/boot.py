#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import re
import sys
import json
import time
import codecs
import hashlib
import logging
import argparse
import importlib
import sysconfig
import subprocess

try:
    import urllib.request as urllib_request
except ImportError:
    import urllib2 as urllib_request

try:
    import urllib.parse as urllib_parse
except ImportError:
    import urlparse as urllib_parse

NAME = "colony-print-boot"
""" The name of the boot program, used as the user agent of the
requests made to the server """

BASE_URL = "https://print.bemisc.com/"
""" The default base URL to be used for the communication with the
Colony Print server, should be the same as the one of the node """

CORE = ("colony-print", "npcolony")
""" The names of the (core) packages that are installed by the update
even when they are not installed, every other package is only updated
in case it's already installed (or required by an updated package) """

TIMEOUT = 30.0
""" The timeout (in seconds) of the listing of the packages """

DOWNLOAD_TIMEOUT = 300.0
""" The timeout (in seconds) of the download of each package """

RETRIES = 3
""" The number of attempts to reach the server for the listing of
the packages, as the network may not be ready when the node boots """

RETRY_DELAY = 10.0
""" The delay (in seconds) between the attempts to reach the server """

CHUNK_SIZE = 65536
""" The size of the chunks (in bytes) used when downloading the
packages and when calculating their digest """

FALSE_VALUES = ("0", "false", "no", "off")
""" The (lower cased) configuration values considered to be false """

TRUE_VALUES = ("1", "true", "yes", "on")
""" The (lower cased) configuration values considered to be true """

PORTS = dict(http=80, https=443)
""" The default port of each scheme, used in the comparison of the
origins of the URLs """

LOOPBACK_HOSTS = ("localhost", "::1")
""" The names of the loopback hosts, besides the 127.0.0.0/8 network,
whose packages are trusted even without HTTPS (eg: tests) """

LOOPBACK_REGEX = re.compile(r"^127\.\d{1,3}\.\d{1,3}\.\d{1,3}\Z")
""" The regular expression that matches the addresses of the loopback
network (127.0.0.0/8), and not the host names that start like them """

WHEEL_REGEX = re.compile(
    r"^(?P<name>[A-Za-z0-9](?:[A-Za-z0-9._]*[A-Za-z0-9])?)"
    r"-(?P<version>[A-Za-z0-9_.!+]+)"
    r"(?:-(?P<build>[0-9][A-Za-z0-9_.]*))?"
    r"-(?P<python>[A-Za-z0-9_.]+)"
    r"-(?P<abi>[A-Za-z0-9_.]+)"
    r"-(?P<platform>[A-Za-z0-9_.]+)\.whl\Z"
)
""" The regular expression that validates the file name of a wheel
package (PEP 427), extracting its name, version and tags, notice that
no path separators (nor line breaks) are allowed in the file name """

NAME_REGEX = re.compile(r"[-_.]+")
""" The regular expression used in the normalization of the name
of a distribution (PEP 503) """

VERSION_REGEX = re.compile(
    r"^v?(?:(?P<epoch>[0-9]+)!)?(?P<release>[0-9]+(?:\.[0-9]+)*)"
    r"(?:[-_.]?(?P<pre>alpha|a|beta|b|preview|pre|c|rc)[-_.]?(?P<pre_n>[0-9]+)?)?"
    r"(?:-(?P<post_i>[0-9]+)|[-_.]?(?P<post>post|rev|r)[-_.]?(?P<post_n>[0-9]+)?)?"
    r"(?:[-_.]?(?P<dev>dev)[-_.]?(?P<dev_n>[0-9]+)?)?"
    r"(?:\+(?P<local>[a-z0-9]+(?:[-_.][a-z0-9]+)*))?\Z"
)
""" The regular expression that splits a (lower cased) version into
its epoch, release, pre, post, development and local parts, according
to the version scheme of PEP 440 """

PRE_RANKS = dict(alpha=0, a=0, beta=1, b=1, preview=2, pre=2, c=2, rc=2)
""" The rank of each phase of a pre release, the final release (no
pre release) has a rank of 3, after all the pre releases """


class SecretRedirectHandler(urllib_request.HTTPRedirectHandler):
    """
    Redirect handler that drops the secret key from the redirected
    requests that leave the origin of the original request (eg: to
    another host or from HTTPS to HTTP), as urllib copies every header
    of the original request into the redirected one, and that refuses
    the redirects to the URLs that are not secure (eg: plain HTTP).
    """

    def __init__(self, boot):
        self.boot = boot

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # the packages are only retrieved from secure URLs, so a redirect
        # to an insecure one (eg: an HTTP mirror) is never followed, as
        # its listing and packages could be replaced on the network
        if not self.boot.secure_url(newurl):
            raise urllib_request.HTTPError(
                newurl, code, "Insecure redirect to '%s'" % newurl, headers, fp
            )
        request = urllib_request.HTTPRedirectHandler.redirect_request(
            self, req, fp, code, msg, headers, newurl
        )
        if request and not self.boot.same_origin(req.get_full_url(), newurl):
            request.headers.pop("X-secret-key", None)
        return request


class ColonyPrintBoot(object):
    """
    Boot sequence of the (Windows) nodes, that updates the packages of
    the node with the ones hosted by the Colony Print server and then
    runs the node, being the entry point of the node (Windows) service.

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
            "--packages",
            default=None,
            help="path to the directory where the packages are kept",
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

        # updates the packages of the node, notice that a failed update
        # never prevents the node from running, as the installed packages
        # keep being used until the next (successful) update
        packages_path = args.packages or os.path.join(
            os.path.dirname(config_path), "packages"
        )
        if not args.no_update and self.update_enabled:
            try:
                self.update(packages_path)
            except Exception as exception:
                logging.exception("Problem updating node: %s" % str(exception))

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

    def update(self, packages_path):
        """
        Updates the packages of the node with the ones hosted by the
        server, installing the newest version of each package that is
        either installed or a core one, when it differs from the one
        that is installed (allowing rollbacks).

        The packages are kept in a local directory, that mirrors the
        (compatible) packages of the server, from which they're installed
        so that the dependencies of the packages are also resolved from
        the packages hosted by the server.

        :type packages_path: String
        :param packages_path: The path to the directory where the packages
        downloaded from the server are kept.
        :rtype: List
        :return: The requirements (name and version) that were installed.
        """

        # the packages are installed and run by the service, so they're
        # only retrieved from a server that is authenticated (HTTPS) or
        # local, unless the insecure update is explicitly allowed
        if not self.packages_secure:
            logging.warning(
                "Skipping update, packages URL '%s' is not HTTPS" % self.packages_url
            )
            return []

        logging.info("Retrieving packages from '%s'" % self.packages_url)
        packages = self.fetch_packages()
        packages = [package for package in packages if self.compatible(package)]
        logging.info("Retrieved %d compatible packages" % len(packages))

        self.sync(packages_path, packages)

        requirements = self.outdated(self.select(packages))
        if not requirements:
            logging.info("Node packages are up to date")
            return []

        logging.info(
            "Updating packages %s"
            % ", ".join("%s==%s" % requirement for requirement in requirements)
        )
        self.install(packages_path, requirements)
        return requirements

    def fetch_packages(self):
        # retrieves the listing of the packages retrying in case the server
        # can't be reached (eg: network not ready on boot), notice that the
        # errors returned by the server itself (HTTP errors) are not retried
        # and that there's always (at least) one attempt
        retries = max(self.retries, 1)
        for attempt in range(retries):
            try:
                data = self.request(self.packages_url, timeout=TIMEOUT)
                break
            except Exception as exception:
                if attempt == retries - 1 or hasattr(exception, "code"):
                    raise
                logging.warning(
                    "Problem retrieving packages (%s), retrying in %.2f seconds"
                    % (str(exception), self.retry_delay)
                )
                time.sleep(self.retry_delay)

        packages = json.loads(data.decode("utf-8"))
        if not isinstance(packages, list):
            raise ValueError("Invalid packages listing")
        return [
            package
            for package in packages
            if isinstance(package, dict) and self.match_wheel(package.get("file", None))
        ]

    def sync(self, packages_path, packages):
        """
        Makes the local directory of the packages mirror the provided
        packages, downloading the ones that are missing (or changed)
        and removing the ones that are no longer hosted by the server.

        :type packages_path: String
        :param packages_path: The path to the directory where the packages
        are kept.
        :type packages: List
        :param packages: The (compatible) packages hosted by the server.
        """

        if not os.path.exists(packages_path):
            os.makedirs(packages_path)

        files = set()
        for package in packages:
            name = package["file"]
            files.add(name)
            file_path = os.path.join(packages_path, name)
            sha256 = package.get("sha256", None)
            if os.path.exists(file_path) and (
                not sha256 or self.digest(file_path) == sha256
            ):
                continue
            logging.info("Downloading package '%s'" % name)
            self.download(name, file_path, sha256=sha256)

        for name in os.listdir(packages_path):
            if name in files:
                continue
            if not name.endswith((".whl", ".tmp")):
                continue
            logging.info("Removing package '%s'" % name)
            os.remove(os.path.join(packages_path, name))

    def download(self, name, file_path, sha256=None):
        url = self.packages_url + "/" + name
        temp_path = file_path + ".tmp"
        response = self.open(url, timeout=DOWNLOAD_TIMEOUT)
        try:
            hash = hashlib.sha256()
            with open(temp_path, "wb") as file:
                while True:
                    chunk = response.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    hash.update(chunk)
                    file.write(chunk)
        except Exception:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            raise
        finally:
            response.close()

        if sha256 and not hash.hexdigest() == sha256:
            os.remove(temp_path)
            raise ValueError("Digest mismatch for package '%s'" % name)

        if os.path.exists(file_path):
            os.remove(file_path)
        os.rename(temp_path, file_path)

    def select(self, packages):
        """
        Selects the newest version of each of the provided packages,
        grouping them by their (normalized) name.

        :type packages: List
        :param packages: The packages from which to select the newest
        version of each of them.
        :rtype: Dictionary
        :return: The map associating the name of each package with
        its newest version.
        """

        versions = dict()
        for package in packages:
            match = self.match_wheel(package["file"])
            name = self.normalize(match.group("name"))
            version = match.group("version").replace("_", "-")
            current = versions.get(name, None)
            if current and self.version_key(current) >= self.version_key(version):
                continue
            versions[name] = version
        return versions

    def outdated(self, versions):
        """
        Determines the requirements (name and version) that must be
        installed so that the installed packages match the provided
        versions, considering only the packages that are installed
        and the core ones.

        :type versions: Dictionary
        :param versions: The map associating the name of each package
        with the version that should be installed.
        :rtype: List
        :return: The sorted list of the requirements (name and version)
        that must be installed.
        """

        requirements = []
        for name, version in sorted(versions.items()):
            installed = self.installed_version(name)
            if installed == None and not name in CORE:
                continue
            if installed and self.version_key(installed) == self.version_key(version):
                continue
            requirements.append((name, version))
        return requirements

    def install(self, packages_path, requirements):
        # installs the newest versions of the requirements, up to the provided
        # ones (allowing rollbacks), using only the mirrored packages (wheels),
        # so that the dependencies are resolved from the packages of the server
        # and the versions that don't support the interpreter (Requires-Python)
        # are skipped by pip, in case any of them is missing the installation
        # fails as a whole (keeping the installed packages), notice that the
        # local part of the versions is not allowed in the upper bound
        command = [
            sys.executable,
            "-m",
            "pip",
            "install",
            "--upgrade",
            "--no-index",
            "--find-links",
            packages_path,
            "--only-binary",
            ":all:",
            "--disable-pip-version-check",
            "--no-warn-script-location",
            "--no-input",
        ]
        command += [
            "%s<=%s" % (name, version.split("+", 1)[0])
            for name, version in requirements
        ]
        code = subprocess.call(command)
        if not code == 0:
            raise RuntimeError("Package installation failed with code %d" % code)

    def compatible(self, package):
        """
        Verifies if the provided package (wheel) is compatible with the
        current Python interpreter and platform, according to its tags.

        :type package: Dictionary
        :param package: The package (with its file name) to be verified.
        :rtype: bool
        :return: If the package may be installed in the current system.
        """

        match = self.match_wheel(package.get("file", None))
        if not match:
            return False
        pairs, platforms = self.tags
        return any(
            (python, abi) in pairs
            for python in match.group("python").split(".")
            for abi in match.group("abi").split(".")
        ) and any(tag in platforms for tag in match.group("platform").split("."))

    def installed_version(self, name):
        try:
            try:
                import importlib.metadata as metadata
            except ImportError:
                metadata = None
            if metadata:
                return metadata.version(name)

            import pkg_resources

            return pkg_resources.get_distribution(name).version
        except Exception:
            return None

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

    def request(self, url, timeout=TIMEOUT):
        response = self.open(url, timeout=timeout)
        try:
            return response.read()
        finally:
            response.close()

    def open(self, url, timeout=TIMEOUT):
        # sends the secret key only to the server (the origin of the base
        # URL) and never to other hosts, including the ones the requests
        # are redirected to (eg: when the packages are hosted elsewhere)
        headers = {"User-Agent": NAME}
        secret_key = self.environ.get("SECRET_KEY", None)
        if secret_key and self.same_origin(url, self.base_url):
            headers["X-Secret-Key"] = secret_key
        request = urllib_request.Request(url, headers=headers)
        opener = urllib_request.build_opener(SecretRedirectHandler(self))
        return opener.open(request, timeout=timeout)

    def same_origin(self, url, other):
        """
        Verifies if the provided URLs have the same origin, meaning the
        same scheme, host and port (the default one of the scheme when
        not defined), as used by browsers.

        :type url: String
        :param url: The URL to be verified.
        :type other: String
        :param other: The other URL to be compared with.
        :rtype: bool
        :return: If both URLs have the same origin.
        """

        url, other = urllib_parse.urlparse(url), urllib_parse.urlparse(other)
        return (
            url.scheme == other.scheme
            and url.hostname == other.hostname
            and (url.port or PORTS.get(url.scheme, None))
            == (other.port or PORTS.get(other.scheme, None))
        )

    def secure_url(self, url):
        """
        Verifies if the provided URL is secure for the retrieval of the
        packages, which are installed and run by the node, meaning that
        it uses HTTPS or targets the local machine (loopback), unless the
        insecure update is explicitly allowed (NODE_UPDATE_INSECURE).

        :type url: String
        :param url: The URL to be verified.
        :rtype: bool
        :return: If the packages may be retrieved from the URL.
        """

        value = self.environ.get("NODE_UPDATE_INSECURE", "0")
        if value.strip().lower() in TRUE_VALUES:
            return True
        url = urllib_parse.urlparse(url)
        if url.scheme == "https":
            return True
        host = url.hostname or ""
        return url.scheme == "http" and (
            host in LOOPBACK_HOSTS or bool(LOOPBACK_REGEX.match(host))
        )

    def digest(self, file_path):
        hash = hashlib.sha256()
        with open(file_path, "rb") as file:
            while True:
                chunk = file.read(CHUNK_SIZE)
                if not chunk:
                    break
                hash.update(chunk)
        return hash.hexdigest()

    def match_wheel(self, name):
        """
        Matches the provided (file) name against the regular expression
        of the wheel packages, so that its name, version and tags may be
        extracted from it.

        :type name: String
        :param name: The (file) name of the package to be matched.
        :rtype: Match
        :return: The match of the name or an invalid value in case the
        name is not the one of a wheel package (or not even a string).
        """

        try:
            return WHEEL_REGEX.match(name)
        except TypeError:
            return None

    def normalize(self, name):
        return NAME_REGEX.sub("-", name).lower()

    def version_key(self, version):
        """
        Builds the (comparable) key of the provided version, following
        the ordering rules of PEP 440 (eg: 1.0.dev1 < 1.0rc1 < 1.0 <
        1.0+local < 1.0.post1.dev1 < 1.0.post1).

        :type version: String
        :param version: The version to build the key for.
        :rtype: Tuple
        :return: The key that orders the version, with the versions
        that are not valid ordered before the valid ones.
        """

        version = version.strip().lower()
        match = VERSION_REGEX.match(version)
        if not match:
            return (-1, version)

        groups = match.groupdict()
        release = [int(value) for value in groups["release"].split(".")]
        while len(release) > 1 and release[-1] == 0:
            release.pop()

        # a release with only a development part (eg: 1.0.dev1) is ordered
        # before its pre releases and the final release after all of them
        if groups["pre"]:
            pre = (PRE_RANKS[groups["pre"]], int(groups["pre_n"] or 0))
        elif groups["dev"] and not groups["post"] and not groups["post_i"]:
            pre = (-1, 0)
        else:
            pre = (3, 0)

        # a release without post part is ordered before its post releases
        # and a release without development part after its development ones
        if groups["post_i"]:
            post = int(groups["post_i"])
        elif groups["post"]:
            post = int(groups["post_n"] or 0)
        else:
            post = -1
        dev = int(groups["dev_n"] or 0) if groups["dev"] else float("inf")

        # a release with a local part is ordered after the one without it,
        # comparing the numeric parts as numbers, after the other parts
        local = ()
        if groups["local"]:
            local = tuple(
                (1, int(part), "") if part.isdigit() else (0, 0, part)
                for part in NAME_REGEX.split(groups["local"])
            )

        return (int(groups["epoch"] or 0), tuple(release), pre, post, dev, local)

    def abi(self, major, minor):
        """
        Builds the ABI tag of the native wheels of CPython for the provided
        version, which includes the pymalloc (m) flag before 3.8 and the wide
        unicode (u) flag for the wide builds of the versions before 3.3.

        :type major: int
        :param major: The major version of CPython.
        :type minor: int
        :param minor: The minor version of CPython.
        :rtype: String
        :return: The ABI tag of CPython for the version (eg: cp37m).
        """

        abi = "cp%d%d" % (major, minor)
        if (major, minor) < (3, 8):
            abi += "m"
        if (major, minor) < (3, 3) and sys.maxunicode == 0x10FFFF:
            abi += "u"
        return abi

    @property
    def tags(self):
        # builds the pairs of python and abi tags supported by the current
        # interpreter, as pip does (PEP 425), the ones of its version, the
        # stable ABI (abi3) of the versions up to it and the pure ones of
        # the versions up to it, together with the supported platforms
        major, minor = sys.version_info[0], sys.version_info[1]
        current = "cp%d%d" % (major, minor)
        abi = self.abi(major, minor)
        pairs = set([(current, abi), (current, "none"), ("py%d" % major, "none")])
        for index in range(minor + 1):
            pairs.add(("py%d%d" % (major, index), "none"))
            if major == 3 and index > 1:
                pairs.add(("cp%d%d" % (major, index), "abi3"))
        platform = sysconfig.get_platform().replace("-", "_").replace(".", "_")
        return pairs, set(["any", platform])

    @property
    def base_url(self):
        base_url = self.environ.get("BASE_URL", None) or BASE_URL
        if not base_url.endswith("/"):
            base_url += "/"
        return base_url

    @property
    def packages_url(self):
        packages_url = self.environ.get("PACKAGES_URL", None)
        packages_url = packages_url or self.base_url + "packages"
        return packages_url.rstrip("/")

    @property
    def packages_secure(self):
        return self.secure_url(self.packages_url)

    @property
    def update_enabled(self):
        value = self.environ.get("NODE_UPDATE", "1")
        return not value.strip().lower() in FALSE_VALUES


if __name__ == "__main__":
    boot = ColonyPrintBoot()
    boot.main()
else:
    __path__ = []
