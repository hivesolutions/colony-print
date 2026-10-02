#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import re
import sys
import glob
import json
import time
import base64
import shutil
import subprocess

try:
    import urllib.request as urllib_request
    import urllib.parse as urllib_parse
    import urllib.error as urllib_error
except ImportError:
    import urllib2 as urllib_request
    import urllib as urllib_parse
    import urllib2 as urllib_error

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_PATH = os.path.join(ROOT, "dist")
WORK_PATH = os.path.join(ROOT, "build", "smoke")
APP_PATH = os.path.join(os.environ.get("ProgramFiles", ""), "Colony Print Node")
DATA_PATH = os.path.join(os.environ.get("ProgramData", ""), "Colony Print Node")
SETUP_LOG_PATH = os.path.join(WORK_PATH, "setup.log")
SERVER_LOG_PATH = os.path.join(WORK_PATH, "server.log")

SERVICE = "colony-print-node"
NODE_ID = "ci-node"
PDF_PRINTER = "Microsoft Print to PDF"
PORT = 8686
BASE_URL = "http://127.0.0.1:%d/" % PORT
PLANTED_URL = b"http://127.0.0.1:1/packages"
PACKAGES_KEY = "ci-packages"

ACCOUNT_SCRIPT = """
import logging, appier_extras, colony_print
app = colony_print.ColonyPrintApp(level=logging.ERROR)
account = appier_extras.admin.Account(
    username="root",
    email="root@colony-print.com",
    password="root",
    password_confirm="root",
    type=appier_extras.admin.Account.ADMIN_TYPE,
)
account.save()
print(account.key)
"""


class Smoke(object):
    """
    Smoke test of the Windows installer of the Colony Print node, meant to
    be run (as administrator) on a disposable machine (eg: the CI runner)
    after the windows\\build.ps1 script, as it installs and uninstalls the
    node and its service.

    Runs a local Colony Print server, that hosts the packages of the node
    with a newer version of colony-print, silently installs the node with
    the server and verifies that the node updates itself, registers itself
    and prints a document, re-installing and uninstalling it at the end,
    installing it once more with the configuration kept by the uninstall.
    """

    def __init__(self):
        self.key = None
        self.server = None

    def run(self):
        if os.path.exists(WORK_PATH):
            shutil.rmtree(WORK_PATH)
        os.makedirs(WORK_PATH)

        try:
            self.start_server()
            version = self.upload_packages()
            self.test_install(version)
            self.test_print()
            self.test_reinstall(version)
            self.test_uninstall()
            self.test_install_kept(version)
        finally:
            self.dump_logs()
            self.stop_server()

    def start_server(self):
        env = dict(os.environ)
        env.update(
            ADAPTER="tiny",
            SERVER="netius",
            HOST="127.0.0.1",
            PORT=str(PORT),
            LEVEL="INFO",
            DATA_PATH=os.path.join(WORK_PATH, "data"),
            PACKAGES_KEY=PACKAGES_KEY,
        )

        # creates the admin account whose secret key is used both by the
        # node and by the requests of the test, running a script file
        script_path = os.path.join(WORK_PATH, "account.py")
        with open(script_path, "wb") as file:
            file.write(ACCOUNT_SCRIPT.encode("utf-8"))
        output = subprocess.check_output(
            [sys.executable, script_path], cwd=WORK_PATH, env=env
        )
        self.key = output.decode("utf-8").strip().splitlines()[-1]

        log("Starting server at %s" % BASE_URL)
        self.server_log = open(SERVER_LOG_PATH, "wb")
        self.server = subprocess.Popen(
            [sys.executable, "-m", "colony_print.main"],
            cwd=WORK_PATH,
            env=env,
            stdout=self.server_log,
            stderr=subprocess.STDOUT,
        )
        wait_for(lambda: self.request("GET", "ping")[0] == 200, "server to start")

    def stop_server(self):
        if not self.server:
            return
        self.server.terminate()
        self.server.wait()
        self.server_log.close()

    def upload_packages(self):
        # uploads the packages built for the node (the ones of the installer)
        # together with a newer version of colony-print, that the node must
        # install when it boots, reporting the newer version
        packages = glob.glob(os.path.join(DIST_PATH, "packages", "*.whl"))
        assert packages, "No packages found in dist"
        version, wheel_path = self.build_newer()
        for path in packages + [wheel_path]:
            name = os.path.basename(path)
            with open(path, "rb") as file:
                data = file.read()

            # the secret key (kept by the node) alone must not be able to
            # publish packages, only together with the packages key
            code, _data = self.request(
                "PUT",
                "packages/" + name,
                data=data,
                content_type="application/octet-stream",
            )
            assert code == 403, "Upload of '%s' without key (%d)" % (name, code)
            code, _data = self.request(
                "PUT",
                "packages/" + name,
                data=data,
                content_type="application/octet-stream",
                headers={"X-Packages-Key": PACKAGES_KEY},
            )
            assert code == 200, "Upload of '%s' failed (%d)" % (name, code)
        log("Uploaded %d packages (colony-print %s)" % (len(packages) + 1, version))
        return version

    def build_newer(self):
        source_path = os.path.join(WORK_PATH, "newer")
        os.makedirs(source_path)
        shutil.copy(os.path.join(ROOT, "setup.py"), source_path)
        shutil.copy(os.path.join(ROOT, "README.md"), source_path)
        shutil.copytree(
            os.path.join(ROOT, "src", "colony_print"),
            os.path.join(source_path, "src", "colony_print"),
            ignore=shutil.ignore_patterns("__pycache__", "test"),
        )

        setup_path = os.path.join(source_path, "setup.py")
        current = re.search(r'version="([^"]+)"', read(setup_path)).group(1)
        version = current + ".post1"
        replace(setup_path, 'version="%s"' % current, 'version="%s"' % version)
        replace(
            os.path.join(source_path, "src", "colony_print", "node.py"),
            'VERSION = "%s"' % current,
            'VERSION = "%s"' % version,
        )

        wheels_path = os.path.join(WORK_PATH, "wheels")
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "pip",
                "wheel",
                "--no-deps",
                "--wheel-dir",
                wheels_path,
                source_path,
            ]
        )
        return version, glob.glob(os.path.join(wheels_path, "*.whl"))[0]

    def test_install(self, version):
        # plants a data directory and a configuration owned (and writable) by
        # the users, as created by any user before the node is installed, that
        # points the node to other packages, which the installer must not use
        config_path = os.path.join(DATA_PATH, "config.env")
        os.makedirs(DATA_PATH)
        with open(config_path, "wb") as file:
            file.write(b"PACKAGES_URL=%s\r\nNODE_NAME=Planted\r\n" % PLANTED_URL)
        subprocess.check_call(
            ["icacls", DATA_PATH, "/grant", "*S-1-5-32-545:(OI)(CI)F"]
        )
        subprocess.check_call(["icacls", DATA_PATH, "/setowner", "*S-1-5-32-545", "/T"])

        # installs the node in email mode when there's a PDF printer, so that
        # the printing of a document may be verified (without email)
        args = [
            "/URL=" + BASE_URL,
            "/KEY=" + self.key,
            "/NAME=CI Node",
            "/LOCATION=GitHub Actions",
        ]
        if PDF_PRINTER in self.printers():
            args += [
                "/MODE=email",
                "/PRINTER=" + PDF_PRINTER,
                "/EMAILS=ci@colony-print.com",
                "/MAILMEKEY=ci",
            ]
        self.install(args)

        assert self.service_state() == "RUNNING", "Service is not running"
        config = read(config_path)
        assert "NODE_ID=%s" % NODE_ID in config, config
        assert "SECRET_KEY=%s" % self.key in config, "Secret key not in config"
        assert not "PACKAGES_URL" in config, "Planted configuration used"
        assert not "Planted" in config, "Planted configuration used"

        for path in (DATA_PATH, config_path):
            acl = subprocess.check_output(["icacls", path]).decode("utf-8", "ignore")
            log(acl)
            assert not "BUILTIN\\Users" in acl, "%s accessible by users" % path

        node = self.wait_node(version)
        assert "npcolony" in node["engines"], node["engines"]
        devices = node["engine_info"]["colony"]["devices"]
        log("Node printers: %s" % ", ".join(device["name"] for device in devices))

        installed = self.installed_version()
        assert installed == version, "Installed %s, expected %s" % (installed, version)

    def test_print(self):
        if not PDF_PRINTER in self.printers():
            log("Skipping print test, no '%s' printer" % PDF_PRINTER)
            return

        code, data = self.request(
            "POST",
            "nodes/%s/print_hello" % NODE_ID,
            data=urllib_parse.urlencode(
                dict(options=json.dumps(dict(send_email=False, save_output=True)))
            ).encode("utf-8"),
            content_type="application/x-www-form-urlencoded",
        )
        assert code == 200, "Print request failed (%d): %s" % (code, data)
        job_id = json.loads(data.decode("utf-8"))["id"]

        def finished():
            code, data = self.request("GET", "jobs/%s" % job_id)
            job = json.loads(data.decode("utf-8"))
            return job if job.get("status", None) == "finished" else None

        job = wait_for(finished, "job %s to finish" % job_id, timeout=180)
        result = job["result"]
        assert result["result"] == "success", "Job failed: %s" % result
        output = base64.b64decode(result["output_data"])
        assert output.startswith(b"%PDF"), "Output is not a PDF document"
        log("Printed document (%d bytes)" % len(output))

    def test_reinstall(self, version):
        # runs the installer once more without any parameter, which must
        # keep the configuration, while replacing the (updated) packages
        # with the ones of the installer, that the node updates once more
        last_ping = self.node()["last_ping"]
        self.install([])
        assert self.service_state() == "RUNNING", "Service is not running"
        assert "SECRET_KEY=%s" % self.key in read(os.path.join(DATA_PATH, "config.env"))
        self.wait_node(version, last_ping=last_ping)

    def test_uninstall(self):
        self.uninstall()
        assert not os.path.exists(os.path.join(APP_PATH, "python")), "Python left"
        assert os.path.exists(os.path.join(DATA_PATH, "config.env")), "Config removed"

    def test_install_kept(self, version):
        # installs the node once more without any parameter, which must use
        # the configuration kept by the uninstall, as the data directory and
        # the configuration written by the installer are trusted (owned by
        # the administrators), even without the service, uninstalling it
        last_ping = self.node()["last_ping"]
        self.install([])
        assert self.service_state() == "RUNNING", "Service is not running"
        assert "SECRET_KEY=%s" % self.key in read(os.path.join(DATA_PATH, "config.env"))
        self.wait_node(version, last_ping=last_ping)
        self.uninstall()

    def uninstall(self):
        uninstaller = os.path.join(APP_PATH, "unins000.exe")
        subprocess.check_call(
            [uninstaller, "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"]
        )
        wait_for(
            lambda: not os.path.exists(uninstaller) and self.service_state() == None,
            "uninstall to finish",
        )

    def install(self, args):
        setups = glob.glob(os.path.join(DIST_PATH, "colony-print-node-setup-*.exe"))
        assert setups, "No installer found in dist"
        log("Installing %s" % os.path.basename(setups[0]))
        code = subprocess.call(
            [
                setups[0],
                "/VERYSILENT",
                "/SUPPRESSMSGBOXES",
                "/NORESTART",
                "/LOG=" + SETUP_LOG_PATH,
            ]
            + args
        )
        assert code == 0, "Installer failed with code %d" % code

    def wait_node(self, version, last_ping=0.0):
        # waits for the node to register itself with the expected version,
        # which means that it updated itself and runs the new version
        def registered():
            node = self.node()
            if not node or node.get("last_ping", 0.0) <= last_ping:
                return None
            return node if node.get("version", None) == version else None

        node = wait_for(registered, "node to register with %s" % version, timeout=300)
        log("Node registered: %s" % json.dumps(node, indent=4))
        return node

    def node(self):
        code, data = self.request("GET", "nodes")
        if not code == 200:
            return None
        return json.loads(data.decode("utf-8")).get(NODE_ID, None)

    def installed_version(self):
        output = subprocess.check_output(
            [
                os.path.join(APP_PATH, "python", "python.exe"),
                "-c",
                "import importlib.metadata as m; print(m.version('colony-print'))",
            ]
        )
        return output.decode("utf-8").strip()

    def service_state(self):
        process = subprocess.Popen(
            ["sc.exe", "query", SERVICE], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        output = process.communicate()[0].decode("utf-8", "ignore")
        match = re.search(r"STATE\s*:\s*\d+\s+(\w+)", output)
        return match.group(1) if match else None

    def printers(self):
        output = subprocess.check_output(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                "Get-Printer | Select-Object -ExpandProperty Name",
            ]
        )
        return [line.strip() for line in output.decode("utf-8", "ignore").splitlines()]

    def request(
        self, method, path, data=None, content_type=None, headers=None, timeout=60
    ):
        headers = dict(headers or dict())
        if self.key:
            headers["X-Secret-Key"] = self.key
        if content_type:
            headers["Content-Type"] = content_type
        request = urllib_request.Request(BASE_URL + path, data=data, headers=headers)
        request.get_method = lambda: method
        try:
            response = urllib_request.urlopen(request, timeout=timeout)
        except urllib_error.HTTPError as error:
            return error.code, error.read()
        except Exception:
            return 0, b""
        try:
            return response.getcode(), response.read()
        finally:
            response.close()

    def dump_logs(self):
        paths = [SETUP_LOG_PATH, SERVER_LOG_PATH]
        paths += sorted(glob.glob(os.path.join(DATA_PATH, "logs", "*.log")))
        for path in paths:
            if not os.path.exists(path):
                continue
            log("==== %s ====" % path)
            log(read(path, errors="replace"))


def wait_for(condition, message, timeout=120, interval=2.0):
    log("Waiting for %s" % message)
    end = time.time() + timeout
    while time.time() < end:
        result = condition()
        if result:
            return result
        time.sleep(interval)
    raise AssertionError("Timeout waiting for %s" % message)


def read(path, errors="strict"):
    with open(path, "rb") as file:
        return file.read().decode("utf-8-sig", errors)


def replace(path, old, new):
    data = read(path)
    assert old in data, "'%s' not found in %s" % (old, path)
    with open(path, "wb") as file:
        file.write(data.replace(old, new).encode("utf-8"))


def log(message):
    sys.stdout.write(message + "\n")
    sys.stdout.flush()


if __name__ == "__main__":
    Smoke().run()
