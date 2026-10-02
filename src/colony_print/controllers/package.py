#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import re
import hmac
import hashlib

import appier

WHEEL_REGEX = re.compile(
    r"^(?P<name>[A-Za-z0-9](?:[A-Za-z0-9._]*[A-Za-z0-9])?)"
    r"-(?P<version>[A-Za-z0-9_.!+]+)"
    r"(?:-(?P<build>[0-9][A-Za-z0-9_.]*))?"
    r"-(?P<python>[A-Za-z0-9_.]+)"
    r"-(?P<abi>[A-Za-z0-9_.]+)"
    r"-(?P<platform>[A-Za-z0-9_.]+)\.whl\Z"
)
""" The regular expression that validates the file name of a
wheel package (PEP 427), the only kind of package hosted by the
server, and that extracts its (distribution) name and version,
notice that no path separators (nor line breaks) are allowed in
the file name """

NAME_REGEX = re.compile(r"[-_.]+")
""" The regular expression used in the normalization of the
name of a distribution (PEP 503) so that names are compared
and listed in a canonical way """

CHUNK_SIZE = 65536
""" The size of the chunks (in bytes) used when reading the
package files for the calculation of their digest """


class PackageController(appier.Controller):
    """
    Controller responsible for the hosting of the (wheel) packages
    that are installed by the (Windows) nodes on their boot, making
    the server the single source of the versions run by the nodes.

    The nodes list the packages, download the ones they don't have
    and install the newest version of each of them, so a version is
    rolled out by uploading its package and rolled back by removing it.

    As the packages are run by every node, uploading and removing them
    also requires the packages key (`PACKAGES_KEY`), sent in the
    `X-Packages-Key` header, which (unlike the secret key) is never
    kept by the nodes, so that a compromised node can't publish them.
    """

    def __init__(self, owner, *args, **kwargs):
        appier.Controller.__init__(self, owner, *args, **kwargs)
        self.digests = dict()

    @appier.route("/packages", "GET", json=True)
    @appier.ensure(token="admin")
    def list(self):
        return self.packages()

    @appier.route("/packages", "OPTIONS")
    def list_o(self):
        return ""

    @appier.route("/packages", "POST", json=True)
    @appier.ensure(token="admin")
    def upload(self):
        # retrieves the complete set of files sent in the (multipart)
        # request and stores each of them as a package, notice that
        # all the files are validated before storing any of them
        self.verify_publish()
        files = self.field("file", [], multiple=True)
        files = [file for file in files if isinstance(file, tuple)]
        appier.verify(files, message="No package files provided", code=400)
        for file in files:
            self.verify_name(file[0])
            appier.verify(file[2], message="No package data provided", code=400)
        return [self.store(file[0], file[2]) for file in files]

    @appier.route("/packages/<str:name>", "GET")
    @appier.ensure(token="admin")
    def show(self, name):
        self.verify_name(name)
        file_path = os.path.join(self.packages_path, name)
        appier.verify(
            os.path.isfile(file_path),
            message="Package not found",
            code=404,
        )
        return self.send_path(file_path, name=name)

    @appier.route("/packages/<str:name>", "OPTIONS")
    def show_o(self, name):
        return ""

    @appier.route("/packages/<str:name>", "PUT", json=True)
    @appier.ensure(token="admin")
    def update(self, name):
        # retrieves the "raw" data of the request, which should contain
        # the contents of the package, and stores it under the name
        self.verify_publish()
        self.verify_name(name)
        data = self.request.get_data()
        appier.verify(data, message="No package data provided", code=400)
        return self.store(name, data)

    @appier.route("/packages/<str:name>", "DELETE", json=True)
    @appier.ensure(token="admin")
    def delete(self, name):
        self.verify_publish()
        self.verify_name(name)
        file_path = os.path.join(self.packages_path, name)
        appier.verify(
            os.path.isfile(file_path),
            message="Package not found",
            code=404,
        )
        os.remove(file_path)
        self.digests.pop(name, None)

    def packages(self):
        """
        Retrieves the information of the complete set of packages
        hosted by the server, sorted by their (file) name.

        :rtype: List
        :return: The list with the information of each package.
        """

        packages_path = self.packages_path
        if not os.path.isdir(packages_path):
            return []
        packages = []
        for name in sorted(os.listdir(packages_path)):
            package = self.package_info(name)
            if not package:
                continue
            packages.append(package)
        return packages

    def store(self, name, data):
        """
        Stores the provided data as the package with the provided
        (file) name, replacing any existing package with that name.

        The data is first written to a temporary file that is then
        moved into place, so that the nodes never download a package
        that is only partially written.

        :type name: String
        :param name: The (file) name of the package to be stored.
        :type data: String
        :param data: The (binary) contents of the package.
        :rtype: Dictionary
        :return: The information of the stored package.
        """

        packages_path = self.packages_path
        if not os.path.exists(packages_path):
            os.makedirs(packages_path)

        file_path = os.path.join(packages_path, name)
        temp_path = file_path + ".tmp"
        with open(temp_path, "wb") as file:
            file.write(data)

        # moves the temporary file into place atomically, so that the package
        # is never missing while replaced, notice that Python 2 has no atomic
        # replace (and its rename fails on Windows when the target exists)
        if hasattr(os, "replace"):
            os.replace(temp_path, file_path)
        else:
            if os.path.exists(file_path):
                os.remove(file_path)
            os.rename(temp_path, file_path)

        self.digests.pop(name, None)
        return self.package_info(name)

    def package_info(self, name):
        """
        Builds the information of the package with the provided (file)
        name, to be used by the nodes to determine the packages they
        need to download and install.

        :type name: String
        :param name: The (file) name of the package.
        :rtype: Dictionary
        :return: The information of the package or an invalid value
        in case the name is not the one of a (valid) package file.
        """

        match = WHEEL_REGEX.match(name)
        if not match:
            return None
        file_path = os.path.join(self.packages_path, name)
        if not os.path.isfile(file_path):
            return None
        return dict(
            name=self.normalize(match.group("name")),
            version=match.group("version").replace("_", "-"),
            file=name,
            size=os.path.getsize(file_path),
            modified=os.path.getmtime(file_path),
            sha256=self.digest(name),
        )

    def digest(self, name):
        """
        Calculates the SHA256 digest of the package with the provided
        (file) name, keeping it in cache for as long as the package
        file is not changed (size and modification time).

        :type name: String
        :param name: The (file) name of the package.
        :rtype: String
        :return: The hexadecimal SHA256 digest of the package.
        """

        file_path = os.path.join(self.packages_path, name)
        key = (os.path.getsize(file_path), os.path.getmtime(file_path))
        cached = self.digests.get(name, None)
        if cached and cached[0] == key:
            return cached[1]

        hash = hashlib.sha256()
        with open(file_path, "rb") as file:
            while True:
                chunk = file.read(CHUNK_SIZE)
                if not chunk:
                    break
                hash.update(chunk)
        digest = hash.hexdigest()

        self.digests[name] = (key, digest)
        return digest

    def verify_name(self, name):
        appier.verify(
            WHEEL_REGEX.match(name or ""),
            message="Invalid package name, must be a wheel file",
            code=400,
        )

    def verify_publish(self):
        # verifies that the request is allowed to publish (upload or remove)
        # packages, with the packages key, compared in constant time, notice
        # that the publishing is disabled when there's no packages key
        packages_key = appier.conf("PACKAGES_KEY", None)
        appier.verify(
            packages_key, message="Publishing of packages is disabled", code=403
        )
        key = self.request.get_header("X-Packages-Key", "")
        appier.verify(
            hmac.compare_digest(
                appier.legacy.bytes(key, encoding="utf-8"),
                appier.legacy.bytes(packages_key, encoding="utf-8"),
            ),
            message="Invalid packages key",
            code=403,
        )

    def normalize(self, name):
        return NAME_REGEX.sub("-", name).lower()

    @property
    def packages_path(self):
        data_path = appier.conf("DATA_PATH", "./data")
        return appier.conf("PACKAGES_PATH", os.path.join(data_path, "packages"))
