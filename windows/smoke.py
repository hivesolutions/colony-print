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

XP = "--xp" in sys.argv[1:]
REPLACE = "--replace" in sys.argv[1:]
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DIST_PATH = os.path.join(ROOT, "dist")
WHEELS_PATH = os.path.join(ROOT, "build", "windows", "wheels")
WORK_PATH = os.path.join(ROOT, "build", "smoke")
XP_SETUP_NAME = "colony-print-node-setup-xp-*.exe"
XP_APP_PATH = os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Colony Print Node")
SETUP_NAME = XP_SETUP_NAME if XP else "colony-print-node-setup-[0-9]*.exe"
APP_PATH = (
    XP_APP_PATH
    if XP
    else os.path.join(os.environ.get("ProgramFiles", ""), "Colony Print Node")
)
DATA_PATH = os.path.join(os.environ.get("ProgramData", ""), "Colony Print Node")
SETUP_LOG_PATH = os.path.join(WORK_PATH, "setup.log")
SERVER_LOG_PATH = os.path.join(WORK_PATH, "server.log")
INDEX_LOG_PATH = os.path.join(WORK_PATH, "index.log")

SERVICE = "colony-print-node"
NODE_ID = "ci-node"
PDF_PRINTER = "Microsoft Print to PDF"
PORT = 8686
BASE_URL = "http://127.0.0.1:%d/" % PORT
INDEX_PORT = 8687
INDEX_URL = "http://127.0.0.1:%d/" % INDEX_PORT
PLANTED_URL = b"http://127.0.0.1:1/"
PACKAGES = ("colony-print", "npcolony")
TRUSTED = ("BUILTIN\\Administrators", "NT AUTHORITY\\SYSTEM")

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

    Runs a local Colony Print server, silently installs the node with the
    server and verifies that the node updates itself from PyPI and registers
    itself, then updates and rolls back the node from a local package index
    (with a newer version of colony-print), prints a document, restarts and
    updates the node through the server, re-installs and uninstalls it,
    installing it once more with the configuration kept by the uninstall
    and then over the service of another installer.

    The installer of the Windows XP nodes (32 bit) is the one tested when
    run with the --xp argument, on any version of Windows, with the Python
    of the node (2.7) updating itself with a pip that is not able to list
    the versions of a package and with a configuration that is not kept by
    the uninstall, as its installer is not able to verify (and trust) it.

    The replacement of the node of each installer by the one of the other
    installer is the one tested when run with the --replace argument, which
    requires both installers.
    """

    def __init__(self):
        self.key = None
        self.server = None
        self.index = None

    def run(self):
        if os.path.exists(WORK_PATH):
            shutil.rmtree(WORK_PATH)
        os.makedirs(WORK_PATH)

        try:
            self.start_server()
            if REPLACE:
                self.test_replace_other()
                return
            current, version = self.start_index()
            self.test_install()
            self.test_update(version)
            self.test_print()
            self.test_rollback(current)
            self.test_control(current, version)
            self.test_reinstall(current)
            self.test_uninstall()
            self.test_install_kept(current)
            self.test_replace()
        finally:
            self.dump_logs()
            self.stop_index()
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

    def start_index(self):
        # builds a local package index (PEP 503, as PyPI) with the wheels of
        # the installer and a newer version of colony-print, served by the
        # (directory listing of the) HTTP server of the standard library
        current, version, wheel_path = self.build_newer()
        index_path = os.path.join(WORK_PATH, "index")
        for path in glob.glob(os.path.join(WHEELS_PATH, "*.whl")) + [wheel_path]:
            name = os.path.basename(path).split("-", 1)[0].replace("_", "-").lower()
            if not name in PACKAGES:
                continue
            if not os.path.exists(os.path.join(index_path, name)):
                os.makedirs(os.path.join(index_path, name))
            shutil.copy(path, os.path.join(index_path, name))

        log("Starting index at %s" % INDEX_URL)
        self.index_log = open(INDEX_LOG_PATH, "wb")
        self.index = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "http.server",
                str(INDEX_PORT),
                "--bind",
                "127.0.0.1",
                "--directory",
                index_path,
            ],
            stdout=self.index_log,
            stderr=subprocess.STDOUT,
        )
        wait_for(lambda: fetch(INDEX_URL + "colony-print/") == 200, "index to start")
        return current, version

    def stop_index(self):
        if not self.index:
            return
        self.index.terminate()
        self.index.wait()
        self.index_log.close()

    def build_newer(self):
        # copies the sources of the package, including the configuration that
        # makes its wheel an universal one, so that it's installed by both the
        # Python of the node and the one of the Windows XP nodes (2.7)
        source_path = os.path.join(WORK_PATH, "newer")
        os.makedirs(source_path)
        shutil.copy(os.path.join(ROOT, "setup.py"), source_path)
        shutil.copy(os.path.join(ROOT, "setup.cfg"), source_path)
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
        return current, version, glob.glob(os.path.join(wheels_path, "*.whl"))[0]

    def test_install(self):
        # plants a data directory and a configuration owned by the administrators
        # but writable by the users, as created by an administrator (or by a user
        # that took the ownership of it) before the node is installed, that points
        # the node to other packages, which the installer must not use
        config_path = os.path.join(DATA_PATH, "config.env")
        os.makedirs(DATA_PATH)
        with open(config_path, "wb") as file:
            file.write(b"NODE_INDEX_URL=%s\r\nNODE_NAME=Planted\r\n" % PLANTED_URL)
        subprocess.check_call(["icacls", DATA_PATH, "/setowner", "*S-1-5-32-544", "/T"])
        subprocess.check_call(
            ["icacls", DATA_PATH, "/grant", "*S-1-5-32-545:(OI)(CI)F"]
        )

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
        assert not "NODE_INDEX_URL" in config, "Planted configuration used"
        assert not "Planted" in config, "Planted configuration used"

        # the path of the wrapper of the service (that has spaces) must be
        # quoted, as another program (eg: C:\Program.exe) is run otherwise
        image = self.service_image(raw=True)
        assert image.startswith('"%s' % APP_PATH), "Service path not quoted"

        # verifies that only the system account and the administrators have
        # access to the data directory and to the configuration, so that the
        # next install trusts them (and any other user can't access them)
        for path in (DATA_PATH, config_path):
            acl = subprocess.check_output(["icacls", path]).decode("utf-8", "ignore")
            log(acl)
            for line in acl.replace(path, "").splitlines():
                if not ":(" in line:
                    continue
                principal = line.strip().split(":(", 1)[0]
                assert principal in TRUSTED, "%s accessible by %s" % (path, principal)

        # the volumes of the runner support the security of their files, so
        # the installer of the Windows XP nodes must not warn about it
        setup_log = read(SETUP_LOG_PATH, errors="replace")
        assert not "no file security" in setup_log, "Volume taken as not secure"
        assert not "application paths" in setup_log, "Application paths found"

        # verifies that the access to the data directory is protected, so
        # that the access of its parent is never inherited by it (eg: when
        # the access of the parent is changed), exposing the secret key
        assert self.protected(DATA_PATH), "Data directory access not protected"

        # the node updates itself from PyPI (the newest versions of the
        # packages of the installer, or newer ones), before registering
        node = self.wait_node()
        assert "npcolony" in node["engines"], node["engines"]
        devices = node["engine_info"]["colony"]["devices"]
        log("Node printers: %s" % ", ".join(device["name"] for device in devices))
        errors = read(os.path.join(DATA_PATH, "logs", "colony-print-node.err.log"))
        assert "Updating packages colony-print, npcolony" in errors, "No update"
        assert not "Problem updating node" in errors, "Update from PyPI failed"

    def test_update(self, version):
        # configures the node to update itself from the local index (instead
        # of PyPI), which must install the newer version of colony-print, that
        # is pinned as PyPI may have a newer version (installed from it)
        last_ping = self.node()["last_ping"]
        self.configure(NODE_INDEX_URL=INDEX_URL, NODE_VERSION=version)
        self.restart()
        self.wait_node(version, last_ping=last_ping)
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

    def test_rollback(self, current):
        # pins the version of colony-print to the one of the installer, which
        # must roll the node back to it (from the local index)
        last_ping = self.node()["last_ping"]
        self.configure(NODE_VERSION=current)
        self.restart()
        self.wait_node(current, last_ping=last_ping)

    def test_control(self, current, version):
        # restarts the node through the server, which must finish the job
        # once the service is running again and the node has registered
        # itself with a newer start time, with the same (pinned) version
        node = self.node()
        for capability in ("restart", "update", "auto-update"):
            assert capability in node["capabilities"], node["capabilities"]
        result = self.command("restart")["result"]
        assert result["result"] == "success", "Restart failed: %s" % result
        assert result["before"]["version"] == current, result["before"]
        assert result["after"]["version"] == current, result["after"]
        assert result["after"]["start_time"] > node["start_time"], "Not restarted"
        assert self.node()["start_time"] == result["after"]["start_time"]
        assert self.service_state() == "RUNNING", "Service is not running"
        errors = read(os.path.join(DATA_PATH, "logs", "colony-print-node.err.log"))
        assert "Restarting node using 'exit'" in errors, "Node not restarted by exit"

        def auto_update():
            node = self.node() or dict()
            return (node.get("update", None) or dict()).get("auto", None)

        # disables the auto-update of the node through the server, which
        # must be kept in the state file of the node (and not in its
        # configuration) and reported by the node
        result = self.command("auto_update", enabled="0")["result"]
        assert result["result"] == "success", "Auto-update failed: %s" % result
        wait_for(lambda: auto_update() == False, "auto-update to be disabled")
        state_path = os.path.join(DATA_PATH, "state.env")
        assert "NODE_UPDATE=0" in read(state_path), "Auto-update not in state"
        assert not "NODE_UPDATE" in read(os.path.join(DATA_PATH, "config.env"))

        # updates the node through the server, which must install the newer
        # version of colony-print (now the pinned one) even with the
        # auto-update disabled, only once (the state file must not keep it)
        self.configure(NODE_VERSION=version)
        result = self.command("update")["result"]
        assert result["result"] == "success", "Update failed: %s" % result
        assert result["before"]["version"] == current, result["before"]
        assert result["after"]["version"] == version, result["after"]
        assert result["update"]["status"] == "success", result["update"]
        assert result["update"]["auto"] == False, result["update"]
        node = self.node()
        assert node["version"] == version, node["version"]
        installed = self.installed_version()
        assert installed == version, "Installed %s, expected %s" % (installed, version)
        assert not "NODE_UPDATE_ONCE" in read(state_path), "Update not consumed"
        assert self.service_state() == "RUNNING", "Service is not running"

        # enables the auto-update once more and pins the version of the
        # installer, as expected by the tests that follow
        result = self.command("auto_update", enabled="1")["result"]
        assert result["result"] == "success", "Auto-update failed: %s" % result
        wait_for(lambda: auto_update() == True, "auto-update to be enabled")
        self.configure(NODE_VERSION=current)

    def test_reinstall(self, current):
        # runs the installer once more without any parameter, which must
        # keep the configuration (including the pinned version and the
        # index), while replacing the packages with the ones of the installer
        last_ping = self.node()["last_ping"]
        self.install([])
        assert self.service_state() == "RUNNING", "Service is not running"
        config = read(os.path.join(DATA_PATH, "config.env"))
        assert "SECRET_KEY=%s" % self.key in config, "Secret key not in config"
        assert "NODE_INDEX_URL=%s" % INDEX_URL in config, "Index not in config"
        assert "NODE_VERSION=%s" % current in config, "Version not in config"
        self.wait_node(current, last_ping=last_ping)

    def test_uninstall(self):
        self.uninstall()
        assert not os.path.exists(os.path.join(APP_PATH, "python")), "Python left"
        assert os.path.exists(os.path.join(DATA_PATH, "config.env")), "Config removed"

    def test_install_kept(self, current):
        # installs the node once more without any parameter, which must use
        # the configuration kept by the uninstall, as the data directory and
        # the configuration written by the installer are trusted (owned by
        # the administrators), even without the service, uninstalling it
        last_ping = self.node()["last_ping"]
        if XP:
            self.test_install_untrusted(last_ping)
            return
        self.install([])
        assert self.service_state() == "RUNNING", "Service is not running"
        assert "SECRET_KEY=%s" % self.key in read(os.path.join(DATA_PATH, "config.env"))
        self.wait_node(current, last_ping=last_ping)
        self.uninstall()

    def test_install_untrusted(self, last_ping):
        # installs the Windows XP node once more, which must not use the
        # configuration kept by the uninstall (its index and its pinned
        # version), as its installer is not able to verify (and trust) it,
        # so that the node is configured by the parameters, uninstalling it,
        # an application path of Python 2.7 (a directory that doesn't exist) is
        # added to the registry for the install, as the installer must warn
        # about it (and continue)
        path = os.path.join(WORK_PATH, "paths")
        path_key = "HKLM\\SOFTWARE\\Python\\PythonCore\\2.7\\PythonPath\\Smoke"
        subprocess.check_call(
            ["reg.exe", "add", path_key, "/ve", "/d", path, "/f", "/reg:32"]
        )
        try:
            self.install(["/URL=" + BASE_URL, "/KEY=" + self.key, "/NAME=CI Node"])
        finally:
            subprocess.check_call(["reg.exe", "delete", path_key, "/f", "/reg:32"])
        setup_log = read(SETUP_LOG_PATH, errors="replace")
        assert "application paths" in setup_log, "No application paths warning"
        assert self.service_state() == "RUNNING", "Service is not running"
        config = read(os.path.join(DATA_PATH, "config.env"))
        assert "SECRET_KEY=%s" % self.key in config, "Secret key not in config"
        assert not "NODE_INDEX_URL" in config, "Untrusted configuration used"
        assert not "NODE_VERSION" in config, "Untrusted configuration used"
        self.wait_node(last_ping=last_ping)
        self.uninstall()

    def test_replace(self):
        # creates a service with the name of the one of the node but with
        # another wrapper (image), as the one of the other installer (of the
        # Windows XP nodes or of the other nodes), and installs the node,
        # which must replace it with its own service, uninstalling it
        last_ping = self.node()["last_ping"]
        image = os.path.join(os.environ.get("SystemRoot", ""), "System32", "cmd.exe")
        subprocess.check_call(["sc.exe", "create", SERVICE, "binPath=", image])
        assert self.service_image() == image, "Service not created"
        self.install(["/URL=" + BASE_URL, "/KEY=" + self.key, "/NAME=CI Node"])
        assert self.service_state() == "RUNNING", "Service is not running"
        image = self.service_image()
        assert image.lower().startswith(APP_PATH.lower()), "Service not replaced"
        self.wait_node(last_ping=last_ping)
        self.uninstall()

    def test_replace_other(self):
        # installs the node and then, without any parameter, the Windows XP
        # node over it and the node over the Windows XP one, each of them must
        # replace the node of the other installer (uninstalling it) and keep
        # its configuration, so that the node registers itself once more with
        # the Python of the installer, uninstalling it
        self.install(["/URL=" + BASE_URL, "/KEY=" + self.key, "/NAME=CI Node"])
        node = self.wait_node()
        assert not "CPython 2.7" in node["platform"], node["platform"]
        for name, path, other_path in (
            (XP_SETUP_NAME, XP_APP_PATH, APP_PATH),
            (SETUP_NAME, APP_PATH, XP_APP_PATH),
        ):
            last_ping = self.node()["last_ping"]
            self.install([], name=name)
            assert self.service_state() == "RUNNING", "Service is not running"
            image = self.service_image()
            assert image.lower().startswith(path.lower() + os.sep), "Not replaced"
            uninstaller = os.path.join(other_path, "unins000.exe")
            wait_for(lambda: not os.path.exists(uninstaller), "other node uninstall")
            config = read(os.path.join(DATA_PATH, "config.env"))
            assert "SECRET_KEY=%s" % self.key in config, "Secret key not in config"
            node = self.wait_node(last_ping=last_ping)
            xp = "CPython 2.7" in node["platform"]
            assert xp == (path == XP_APP_PATH), node["platform"]
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

    def configure(self, **values):
        # sets the provided values in the configuration of the node, keeping
        # its other values, as done by an administrator
        config_path = os.path.join(DATA_PATH, "config.env")
        lines = [
            line
            for line in read(config_path).splitlines()
            if not line.split("=", 1)[0].strip() in values
        ]
        lines += ["%s=%s" % item for item in sorted(values.items())]
        with open(config_path, "wb") as file:
            file.write("\r\n".join(lines + [""]).encode("utf-8"))

    def restart(self):
        subprocess.check_call(["net", "stop", SERVICE])
        subprocess.check_call(["net", "start", SERVICE])

    def command(self, name, **values):
        # queues the command for the node (through its endpoint of the
        # server) and waits for its job to finish, returning the job
        code, data = self.request(
            "POST",
            "nodes/%s/%s" % (NODE_ID, name),
            data=urllib_parse.urlencode(values).encode("utf-8"),
            content_type="application/x-www-form-urlencoded",
        )
        assert code == 200, "Command %s failed (%d): %s" % (name, code, data)
        job_id = json.loads(data.decode("utf-8"))["id"]

        def finished():
            code, data = self.request("GET", "jobs/%s" % job_id)
            job = json.loads(data.decode("utf-8"))
            return job if job.get("status", None) == "finished" else None

        job = wait_for(finished, "command %s to finish" % name, timeout=300)
        log("Command %s finished: %s" % (name, json.dumps(job, indent=4)))
        return job

    def install(self, args, name=SETUP_NAME):
        setups = glob.glob(os.path.join(DIST_PATH, name))
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

    def wait_node(self, version=None, last_ping=0.0):
        # waits for the node to register itself with the expected version
        # (any version when not provided), which means that it updated
        # itself and runs the new version
        def registered():
            node = self.node()
            if not node or node.get("last_ping", 0.0) <= last_ping:
                return None
            if version == None:
                return node
            return node if node.get("version", None) == version else None

        node = wait_for(
            registered,
            "node to register with %s" % (version or "any version"),
            timeout=300,
        )
        log("Node registered: %s" % json.dumps(node, indent=4))
        return node

    def node(self):
        code, data = self.request("GET", "nodes")
        if not code == 200:
            return None
        return json.loads(data.decode("utf-8")).get(NODE_ID, None)

    def installed_version(self):
        # the Python of the Windows XP nodes (2.7) has no metadata module,
        # the resources module bundled with its pip being used instead
        script = "import importlib.metadata as m; print(m.version('colony-print'))"
        if XP:
            script = (
                "from pip._vendor import pkg_resources as r; "
                "print(r.get_distribution('colony-print').version)"
            )
        output = subprocess.check_output(
            [os.path.join(APP_PATH, "python", "python.exe"), "-c", script]
        )
        return output.decode("utf-8").strip()

    def service_state(self):
        process = subprocess.Popen(
            ["sc.exe", "query", SERVICE], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        output = process.communicate()[0].decode("utf-8", "ignore")
        match = re.search(r"STATE\s*:\s*\d+\s+(\w+)", output)
        return match.group(1) if match else None

    def service_image(self, raw=False):
        process = subprocess.Popen(
            ["sc.exe", "qc", SERVICE], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        output = process.communicate()[0].decode("utf-8", "ignore")
        match = re.search(r"BINARY_PATH_NAME\s*:\s*(.+)", output)
        if not match:
            return None
        image = match.group(1).strip()
        return image if raw else image.strip('"')

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

    def protected(self, path):
        # the access is retrieved directly with .NET, as the security module
        # of PowerShell may not be loaded (eg: the one of another PowerShell)
        output = subprocess.check_output(
            [
                "powershell.exe",
                "-NoProfile",
                "-Command",
                "[System.IO.Directory]::GetAccessControl('%s').AreAccessRulesProtected"
                % path,
            ]
        )
        return output.decode("utf-8", "ignore").strip() == "True"

    def request(self, method, path, data=None, content_type=None, timeout=60):
        headers = {"X-Secret-Key": self.key} if self.key else dict()
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
        paths = [SETUP_LOG_PATH, SERVER_LOG_PATH, INDEX_LOG_PATH]
        paths += sorted(glob.glob(os.path.join(DATA_PATH, "logs", "*.log")))
        for path in paths:
            if not os.path.exists(path):
                continue
            log("==== %s ====" % path)
            log(read(path, errors="replace"))


def fetch(url, timeout=10):
    try:
        response = urllib_request.urlopen(url, timeout=timeout)
    except Exception:
        return 0
    try:
        return response.getcode()
    finally:
        response.close()


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
