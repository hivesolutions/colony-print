#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import re
import sys
import json
import zlib
import base64
import shutil
import hashlib
import struct
import tempfile
import unittest

import PIL
import appier
import reportlab
import appier_extras

import colony_print.node

FONTS_PATH = os.path.join(
    os.path.dirname(__file__), "..", "..", "..", "assets", "fonts"
)
""" The path to the directory that contains the fonts bundled
with the repository, used by the binie documents of the tests """

RECEIPT_DEVICE = dict(
    name="Receipt",
    is_default=False,
    media="RP80x297",
    width=226.77,
    length=841.89,
    left=11.34,
    bottom=0.0,
    right=215.43,
    top=841.89,
    custom=dict(
        min_width=72.0,
        min_length=72.0,
        max_width=227.0,
        max_length=9288.0,
        margin_left=11.34,
        margin_bottom=0.0,
        margin_right=11.34,
        margin_top=0.0,
    ),
)
""" The device of an 80 mm receipt printer, as reported by npcolony
for a CUPS queue (sizes in points, printable area 72 mm wide), that
accepts custom paper sizes up to the width of its roll """

OFFICE_DEVICE = dict(
    name="office",
    is_default=True,
    media="A4",
    width=595.28,
    length=841.89,
    left=12.0,
    bottom=12.0,
    right=583.28,
    top=829.89,
    custom=dict(
        min_width=278.99,
        min_length=419.5,
        max_width=612.0,
        max_length=1008.0,
        margin_left=12.0,
        margin_bottom=12.0,
        margin_right=12.0,
        margin_top=12.0,
    ),
)
""" The device of an A4 office printer (the default printer), as
reported by npcolony for a CUPS queue (sizes in points), that accepts
custom paper sizes from 98 x 148 mm to 216 x 356 mm """

LABEL_B64 = base64.b64encode(
    base64.b64decode(colony_print.controllers.node.HELLO_WORLD_B64)[:256]
    + struct.pack("<II", 800, 80)
    + base64.b64decode(colony_print.controllers.node.HELLO_WORLD_B64)[264:]
).decode("utf-8")
""" The hello world binie document with the size (80 x 8 mm) of a
product label, as the ones printed by Omni """

COLONIA_B64 = base64.b64encode(
    base64.b64decode(colony_print.controllers.node.HELLO_WORLD_B64).replace(
        b"Calibri", b"Colonia"
    )
).decode("utf-8")
""" The hello world binie document using the Colonia font, a font
that is not installed in the system (only installed on demand) """

XMPL = '<?xml version="1.0" encoding="UTF-8"?>\
    <printing_document name="hello_world" font="%s" font_size="9">\
        %s\
        <paragraph text_align="center">\
            <line><text>Hello World</text></line>\
        </paragraph>\
    </printing_document>'
""" The template of the hello world XMPL document, with the name
of its font and its font elements (declarations) """


def build_font(name="Colonia"):
    """
    Builds a true type font file from the Calibri font bundled with the
    repository, renaming its family into the provided name, so that the
    font is not installed in the system.

    :type name: String
    :param name: The name of the family of the font, with the same
    size of the original name (Calibri), as the names are replaced.
    :rtype: String
    :return: The contents of the built font file.
    """

    with open(os.path.join(FONTS_PATH, "calibri.ttf"), "rb") as file:
        data = file.read()
    data = data.replace(b"Calibri", name.encode("utf-8"))
    return data.replace("Calibri".encode("utf-16-be"), name.encode("utf-16-be"))


class MockGravostyleAPI(object):
    """
    Stand-in for gravo pilot's GravostyleAPI that records the keyword
    arguments passed to write_text, so that the flag forwarding done by
    the node can be inspected without driving the real software.
    """

    calls = []

    def write_text(self, text, **kwargs):
        MockGravostyleAPI.calls.append(kwargs)
        return []


class MockGravoPilot(object):
    """
    Stand-in for the gravo pilot module that exposes the minimal
    surface used by the node, namely the GravostyleAPI class and the
    capture_logs context manager, so that _handle_gravo can be
    exercised without the real dependency installed.
    """

    GravostyleAPI = MockGravostyleAPI

    @staticmethod
    def capture_logs(*args, **kwargs):
        import contextlib

        @contextlib.contextmanager
        def _capture():
            yield []

        return _capture()


class MockNPColony(object):
    """
    Stand-in for the npcolony module that exposes a configurable format
    and set of devices and records the documents sent for printing, so
    that the conversion of binie documents done by the node for the PDF
    (CUPS) systems can be exercised without printers.
    """

    format = "pdf"
    devices = []
    calls = []

    @staticmethod
    def get_format():
        return MockNPColony.format

    @staticmethod
    def get_devices():
        return MockNPColony.devices

    @staticmethod
    def print_printer_base64(printer, data_b64, options=None):
        options = options or dict()
        MockNPColony.calls.append((printer, data_b64, dict(options)))
        output_path = options.get("output_path", None)
        if output_path:
            with open(output_path, "wb") as file:
                file.write(base64.b64decode(data_b64))
        return 0

    @staticmethod
    def print_base64(data_b64):
        MockNPColony.calls.append((None, data_b64, dict()))


class MockNPColonyWindows(object):
    """
    Stand-in for the npcolony module of windows systems, that prints the
    binie documents (through GDI) and loads the fonts installed on demand
    in the system, recording both the printed documents and the fonts.
    """

    calls = []
    fonts = []
    features = ["load-fonts"]
    errors = dict()

    @staticmethod
    def get_format():
        return "binie"

    @staticmethod
    def get_devices():
        return []

    @staticmethod
    def get_features():
        return MockNPColonyWindows.features

    @staticmethod
    def print_printer_base64(printer, data_b64, options=None):
        MockNPColonyWindows.calls.append((printer, data_b64, dict(options or dict())))

    @staticmethod
    def load_font(path):
        if path in MockNPColonyWindows.errors:
            raise MockNPColonyWindows.errors[path]
        MockNPColonyWindows.fonts.append(("load", path))

    @staticmethod
    def unload_font(path):
        if path in MockNPColonyWindows.errors:
            raise MockNPColonyWindows.errors[path]
        MockNPColonyWindows.fonts.append(("unload", path))


class MockNPColonyLegacy(object):
    """
    Stand-in for a legacy version of the npcolony module that is not
    able to report the format of the documents it prints.
    """

    @staticmethod
    def print_base64(data_b64):
        pass


class MockLibrary(object):
    """
    Stand-in for the module of a library that exposes only its version,
    so that the versions of the libraries reported by the node can be
    verified without the real dependency installed.
    """

    VERSION = "1.0.0"


class MockPlatform(object):
    """
    Stand-in for the platform module that describes a configurable
    operating system (name, release, version and machine), so that
    the information of the system reported by the node can be verified
    in any machine.
    """

    uname = ("Linux", "6.8.0-45-generic", "#45-Ubuntu SMP", "x86_64")

    @staticmethod
    def system():
        return MockPlatform.uname[0]

    @staticmethod
    def release():
        return MockPlatform.uname[1]

    @staticmethod
    def version():
        return MockPlatform.uname[2]

    @staticmethod
    def machine():
        return MockPlatform.uname[3]


class MockInterrupt(BaseException):
    """
    Interruption raised by the stand-in of the server, that is not
    handled by the (endless) loop of the node, so that the loop can be
    exercised for a single iteration.
    """

    pass


class MockServer(object):
    """
    Stand-in for the post operation of appier that records the requests
    posted to the server and then interrupts the node, so that the
    information submitted by the loop of the node can be inspected
    without a server.
    """

    calls = []

    @staticmethod
    def post(url, data_j=None, headers=None):
        MockServer.calls.append((url, data_j, headers))
        raise MockInterrupt()


class MockQueue(object):
    """
    Stand-in for the get and post operations of appier that serves the
    configured batches of jobs to the node, interrupting it once there
    are no more batches, and records the requests posted to the server
    (failing the ones of the results with the configured error), so that
    the handling of the jobs by the loop of the node can be inspected.
    """

    batches = []
    calls = []
    error = None

    @staticmethod
    def get(url, headers=None, timeout=None):
        if not MockQueue.batches:
            raise MockInterrupt()
        return MockQueue.batches.pop(0)

    @staticmethod
    def post(url, data_j=None, headers=None):
        MockQueue.calls.append((url, data_j, headers))
        if MockQueue.error and url.endswith("/result"):
            raise MockQueue.error


class MockSys(object):
    """
    Stand-in for the sys module that exposes a configurable command line
    (the original one of the interpreter and the one of its script) and
    records the exit codes of the node, interrupting it (as the exit of
    the process does), so that the restart of the node can be exercised
    without exiting.
    """

    executable = "/usr/bin/python"
    argv = ["boot.py", "--config", "config.env"]
    orig_argv = ["python", "-I", "-u", "boot.py", "--config", "config.env"]
    exits = []

    @staticmethod
    def exit(code=0):
        MockSys.exits.append(code)
        raise MockInterrupt()


class MockSysLegacy(object):
    """
    Stand-in for the sys module of the interpreters that don't keep their
    original command line (older than Python 3.10), only the one of their
    script (without the options of the interpreter).
    """

    executable = "/usr/bin/python"
    argv = ["boot.py", "--config", "config.env"]
    exit = staticmethod(MockSys.exit)


class MockOS(object):
    """
    Stand-in for the os module that exposes a configurable system (name)
    and environment and records the processes that replace the one of the
    node, interrupting it (as a replaced process never returns) or raising
    the configured error, so that the restart of the node can be exercised
    in any system.
    """

    name = "posix"
    environ = dict()
    execs = []
    error = None

    @staticmethod
    def execve(path, args, env):
        if MockOS.error:
            raise MockOS.error
        MockOS.execs.append((path, args, env))
        raise MockInterrupt()


class MockSubprocess(object):
    """
    Stand-in for the subprocess module that records the processes that
    are started (and their environments) or raises the configured error,
    so that the restart of the node can be exercised without starting
    another node.
    """

    calls = []
    error = None

    @staticmethod
    def Popen(args, env=None):
        if MockSubprocess.error:
            raise MockSubprocess.error
        MockSubprocess.calls.append((args, env))


class ColonyPrintNodeTest(unittest.TestCase):
    def setUp(self):
        self.node = colony_print.node.ColonyPrintNode()
        self.target_dir = tempfile.mkdtemp(prefix="colony-print-fonts-test-")
        self.fonts_dir = tempfile.mkdtemp(prefix="colony-print-fonts-cache-test-")
        self.node.font_cache = colony_print.FontCache(self.fonts_dir)
        MockNPColonyWindows.calls = []
        MockNPColonyWindows.fonts = []
        MockNPColonyWindows.features = ["load-fonts"]
        MockNPColonyWindows.errors = dict()
        MockGravostyleAPI.calls = []
        self._gravo_pilot = sys.modules.get("gravo_pilot")
        sys.modules["gravo_pilot"] = MockGravoPilot
        MockNPColony.format = "pdf"
        MockNPColony.devices = [RECEIPT_DEVICE, OFFICE_DEVICE]
        MockNPColony.calls = []
        self._npcolony = sys.modules.get("npcolony")
        sys.modules["npcolony"] = MockNPColony
        MockPlatform.uname = ("Linux", "6.8.0-45-generic", "#45-Ubuntu SMP", "x86_64")
        self._platform = colony_print.node.platform
        colony_print.node.platform = MockPlatform
        self.os_release_path = os.path.join(self.target_dir, "os-release")
        self._os_release_paths = colony_print.node.OS_RELEASE_PATHS
        colony_print.node.OS_RELEASE_PATHS = (self.os_release_path,)
        MockServer.calls = []
        MockQueue.batches = []
        MockQueue.calls = []
        MockQueue.error = None
        self._get = appier.get
        self._post = appier.post
        MockSys.exits = []
        MockOS.name = "posix"
        MockOS.environ = dict()
        MockOS.execs = []
        MockOS.error = None
        MockSubprocess.calls = []
        MockSubprocess.error = None
        self._sys = colony_print.node.sys
        self._os = colony_print.node.os
        self._execve = os.execve
        self._subprocess = colony_print.node.subprocess
        self.state_path = os.path.join(self.target_dir, "state.env")
        self._font_paths = colony_print.printing.pdf.visitor.FONT_PATHS
        colony_print.printing.pdf.visitor.FONT_PATHS = (os.path.join(FONTS_PATH, ""),)

    def tearDown(self):
        shutil.rmtree(self.target_dir, ignore_errors=True)
        shutil.rmtree(self.fonts_dir, ignore_errors=True)
        if self._gravo_pilot == None:
            sys.modules.pop("gravo_pilot", None)
        else:
            sys.modules["gravo_pilot"] = self._gravo_pilot
        if self._npcolony == None:
            sys.modules.pop("npcolony", None)
        else:
            sys.modules["npcolony"] = self._npcolony
        colony_print.node.platform = self._platform
        colony_print.node.OS_RELEASE_PATHS = self._os_release_paths
        appier.get = self._get
        appier.post = self._post
        colony_print.node.sys = self._sys
        colony_print.node.os = self._os
        os.execve = self._execve
        colony_print.node.subprocess = self._subprocess
        colony_print.printing.pdf.visitor.FONT_PATHS = self._font_paths

    def _gravo_payload(self, **kwargs):
        data = dict(text="Hello World")
        data.update(kwargs)
        return base64.b64encode(json.dumps(data).encode("utf-8"))

    def _os_release(self, data, path=None):
        with open(path or self.os_release_path, "wb") as file:
            file.write(data)

    def _font(self, name="Colonia", **kwargs):
        font = dict(name=name, data_b64=base64.b64encode(build_font(name)).decode())
        font.update(kwargs)
        return font

    def _xmpl(self, font_name="Calibri", fonts=[]):
        elements = "".join(
            "<font %s/>" % " ".join('%s="%s"' % item for item in sorted(font.items()))
            for font in fonts
        )
        data = XMPL % (font_name, elements)
        return base64.b64encode(data.encode("utf-8")).decode("utf-8")

    def _hello_world(self, data_b64):
        # verifies that the binie document is the hello world one, as
        # converted from the hello world XMPL document (with its title)
        data = base64.b64decode(data_b64)
        hello_world = base64.b64decode(colony_print.controllers.node.HELLO_WORLD_B64)
        return (
            data[:256].rstrip(b"\0") == b"hello_world"
            and data[256:] == hello_world[256:]
        )

    def _loop(self, **values):
        # runs the loop of the node with the provided configuration values
        # (and the font cache of the test) until it's interrupted by one of
        # the stand-ins (the ones of the server and of the exit), note that
        # any other problem is retried by the loop, without sleeping
        values = dict(values, FONTS_PATH=self.fonts_dir)
        for name, value in values.items():
            appier.conf_s(name, value)
        self.node.sleep_time = 0.0
        try:
            self.assertRaises(MockInterrupt, self.node.loop)
        finally:
            for name in values:
                appier.conf_r(name)

    def _urls(self, calls):
        return [url.split("nodes/", 1)[1] for url, _data_j, _headers in calls]

    def _state(self, path=None):
        with open(path or self.state_path, "rb") as file:
            return file.read()

    def _media_box(self, data_b64):
        data = base64.b64decode(data_b64)
        pattern = b"/MediaBox \\[ (\\S+) (\\S+) (\\S+) (\\S+) \\]"
        return tuple(float(value) for value in re.search(pattern, data).groups())

    def _pages(self, data_b64):
        data = base64.b64decode(data_b64)
        return len(re.findall(b"/Type /Page\\b", data))

    def _contents(self, data_b64):
        # extracts the (decompressed) content streams of the pages from
        # the PDF document, the ones that contain drawing operations
        data = base64.b64decode(data_b64)
        contents = []
        for match in re.finditer(b"<<([^>]*?)>>\\s*stream\\r?\\n", data):
            if not b"FlateDecode" in match.group(1):
                continue
            end = data.index(b"endstream", match.end())
            try:
                content = zlib.decompress(data[match.end() : end])
            except Exception:
                continue
            if not b" Tf " in content:
                continue
            contents.append(content)
        return contents

    def test_loop(self):
        # the information of the node is posted to the server as JSON,
        # so the versions of its libraries and the information of its
        # system must be JSON serializable, note that the invalid sleep
        # time makes any other problem fail the test, instead of being
        # retried forever by the loop
        sys.modules["gravo_pilot"] = MockLibrary
        self._os_release(b'PRETTY_NAME="Ubuntu 24.04.1 LTS"\n')
        colony_print.FontCache(self.fonts_dir).install(self._font())
        appier.post = MockServer.post
        appier.conf_s("FONTS_PATH", self.fonts_dir)
        self.node.sleep_time = None
        try:
            self.assertRaises(MockInterrupt, self.node.loop)
        finally:
            appier.conf_r("FONTS_PATH")
        self.assertEqual(len(MockServer.calls), 1)

        url, data_j, _headers = MockServer.calls[0]
        self.assertEqual("nodes/" in url, True)
        self.assertEqual(data_j["version"], colony_print.node.VERSION)
        self.assertEqual(data_j["libraries"], self.node.libraries)
        self.assertEqual(data_j["libraries"]["gravo_pilot"], "1.0.0")
        self.assertEqual(data_j["system"], self.node.system)
        self.assertEqual(data_j["system"]["distribution"], "Ubuntu 24.04.1 LTS")
        self.assertEqual(data_j["capabilities"], self.node.capabilities)
        self.assertEqual("dynamic-fonts" in data_j["capabilities"], True)
        self.assertEqual(data_j["start_time"], self.node.start_time)
        self.assertEqual(type(data_j["start_time"]), float)
        self.assertEqual(data_j["update"], None)
        self.assertEqual(self.node.font_cache.path, self.fonts_dir)
        self.assertEqual(
            [(font["name"], font["active"]) for font in data_j["fonts"]],
            [("Colonia", True)],
        )
        self.assertEqual(json.loads(json.dumps(data_j)), data_j)

    def test_loop_fonts_error(self):
        # a font of the cache that fails to load in the system (windows) is
        # logged and doesn't prevent the node from submitting its information
        info = colony_print.FontCache(self.fonts_dir).install(self._font())
        sys.modules["npcolony"] = MockNPColonyWindows
        MockNPColonyWindows.errors = {info["path"]: IOError("Problem loading font")}
        appier.post = MockServer.post
        appier.conf_s("FONTS_PATH", self.fonts_dir)
        self.node.sleep_time = None
        try:
            self.assertRaises(MockInterrupt, self.node.loop)
        finally:
            appier.conf_r("FONTS_PATH")
        self.assertEqual(len(MockServer.calls), 1)
        self.assertEqual(self.node.loaded_fonts, set())
        self.assertEqual(len(MockServer.calls[0][1]["fonts"]), 1)

    def test_loop_control(self):
        # the node restarts itself by running its own command line once more,
        # unless it's run by the windows service (WinSW), that starts again a
        # node that exits, or the way to restart is configured, any other
        # value refusing the restart (that is not advertised)
        appier.post = MockServer.post
        for values, restart in (
            (dict(), "exec"),
            (dict(WINSW_SERVICE_ID="colony-print-node"), "exit"),
            (dict(WINSW_SERVICE_ID="colony-print-node", NODE_RESTART="exec"), "exec"),
            (dict(NODE_RESTART=" Exit "), "exit"),
            (dict(NODE_RESTART=""), "exec"),
            (dict(NODE_RESTART="0"), None),
            (dict(NODE_RESTART=0), None),
            (dict(NODE_RESTART="reboot"), None),
        ):
            self._loop(**values)
            data_j = MockServer.calls[-1][1]
            self.assertEqual(self.node.node_restart, restart)
            self.assertEqual("restart" in data_j["capabilities"], not restart == None)
            self.assertEqual("update" in data_j["capabilities"], False)
            self.assertEqual("auto-update" in data_j["capabilities"], False)
            self.assertEqual(data_j["update"], None)

        # the node run by the boot is told about it, about its state file
        # and about the outcome of the update, that is submitted to the
        # server together with the capabilities that depend on the boot
        values = dict(
            NODE_BOOT="1",
            NODE_STATE_PATH=self.state_path,
            NODE_UPDATE_STATUS="failure",
            NODE_UPDATE_TIME="1790879619.9",
            NODE_UPDATE_ERROR="Package update failed with code 1",
        )
        self._loop(**values)
        data_j = MockServer.calls[-1][1]
        self.assertEqual(self.node.node_boot, True)
        self.assertEqual(self.node.node_state, self.state_path)
        self.assertEqual(
            data_j["capabilities"][-3:], ["restart", "update", "auto-update"]
        )
        self.assertEqual(
            data_j["update"],
            dict(
                auto=True,
                status="failure",
                time=1790879619.9,
                error="Package update failed with code 1",
            ),
        )
        self.assertEqual(json.loads(json.dumps(data_j)), data_j)

        # the auto-update of the node is the one of its configuration (as
        # applied by the boot), disabled by the false values of the boot
        for value, auto in (("0", False), (" Off ", False), ("yes", True), ("", True)):
            self._loop(NODE_UPDATE=value, **values)
            self.assertEqual(self.node.node_update, auto)
            self.assertEqual(MockServer.calls[-1][1]["update"]["auto"], auto)

        # the node that can't restart is not updated from the admin, but
        # its auto-update is still set from it
        self._loop(NODE_RESTART="0", **values)
        self.assertEqual(MockServer.calls[-1][1]["capabilities"][-1], "auto-update")
        self.assertEqual("update" in MockServer.calls[-1][1]["capabilities"], False)

        # the remote control of the node disabled in its configuration, no
        # capability of it being advertised, with the update still reported
        for value in ("0", "false", "no", "off"):
            self._loop(NODE_CONTROL=value, **values)
            data_j = MockServer.calls[-1][1]
            self.assertEqual(self.node.node_control, False)
            for capability in ("restart", "update", "auto-update"):
                self.assertEqual(capability in data_j["capabilities"], False)
            self.assertEqual(data_j["update"]["status"], "failure")
        self._loop(NODE_CONTROL="1", **values)
        self.assertEqual(self.node.node_control, True)

    def test_loop_restart(self):
        # the restart requested by a job is only done once the remaining jobs
        # of its batch are printed and their results posted, the job having
        # no result (it's finished by the server once the node is back) and
        # the next batch of jobs not being retrieved by the node
        data_b64 = base64.b64encode(b"Hello World").decode("utf-8")
        MockQueue.batches = [
            [
                dict(id="first", name="first", type="text", data_b64=data_b64),
                dict(id="restart", name="restart", type="restart"),
                dict(id="second", name="second", type="text", data_b64=data_b64),
            ],
            [dict(id="third", name="third", type="text", data_b64=data_b64)],
        ]
        appier.get = MockQueue.get
        appier.post = MockQueue.post
        colony_print.node.sys = MockSys
        self._loop(NODE_RESTART="exit")
        self.assertEqual(MockSys.exits, [colony_print.node.RESTART_CODE])
        urls = self._urls(MockQueue.calls)
        self.assertEqual(urls[0], "node")
        self.assertEqual(
            sorted(urls[1:]), ["node/jobs/first/result", "node/jobs/second/result"]
        )
        self.assertEqual(
            [data_j["result"] for _url, data_j, _headers in MockQueue.calls[1:]],
            ["success", "success"],
        )
        self.assertEqual(len(MockQueue.batches), 1)
        self.assertEqual(self.node.restart_jobs, [])

        # the node also restarts when the results of the batch can't be
        # posted, instead of waiting for the next batch of jobs
        MockSys.exits = []
        MockQueue.calls = []
        MockQueue.error = appier.HTTPError("Problem posting result")
        MockQueue.batches = [
            [
                dict(id="first", name="first", type="text", data_b64=data_b64),
                dict(id="update", name="update", type="update"),
            ],
            [dict(id="third", name="third", type="text", data_b64=data_b64)],
        ]
        self._loop(NODE_RESTART="exit", NODE_BOOT="1", NODE_STATE_PATH=self.state_path)
        self.assertEqual(MockSys.exits, [colony_print.node.RESTART_CODE])
        self.assertEqual(
            self._urls(MockQueue.calls), ["node", "node/jobs/first/result"]
        )
        self.assertEqual(len(MockQueue.batches), 1)
        self.assertEqual(self._state(), b"NODE_UPDATE_ONCE=1\r\n")

    def test_loop_restart_error(self):
        # a restart that fails is posted as the (error) result of the job
        # that requested it, the node running (and registering) as before
        MockQueue.batches = [[dict(id="restart", name="restart", type="restart")]]
        MockOS.error = OSError("Exec format error")
        appier.get = MockQueue.get
        appier.post = MockQueue.post
        colony_print.node.sys = MockSys
        os.execve = MockOS.execve
        self._loop(NODE_RESTART="exec")
        self.assertEqual(MockSys.exits, [])
        self.assertEqual(
            self._urls(MockQueue.calls), ["node", "node/jobs/restart/result", "node"]
        )
        result = MockQueue.calls[1][1]
        self.assertEqual(result["result"], "error")
        self.assertEqual(result["error"], "Exec format error")
        self.assertEqual("OSError" in result["traceback"], True)
        self.assertEqual(self.node.restart_jobs, [])

        # the commands that the node doesn't support (eg: with its remote
        # control disabled after they were queued) fail as any other job,
        # with their results posted and without any restart
        MockQueue.calls = []
        MockQueue.batches = [
            [
                dict(id="restart", name="restart", type="restart"),
                dict(id="update", name="update", type="update"),
                dict(
                    id="auto-update",
                    name="auto-update",
                    type="auto-update",
                    options=dict(enabled=False),
                ),
            ]
        ]
        self._loop(NODE_CONTROL="0", NODE_BOOT="1", NODE_STATE_PATH=self.state_path)
        urls = self._urls(MockQueue.calls)
        self.assertEqual((urls[0], urls[-1]), ("node", "node"))
        self.assertEqual(
            dict(
                (url, data_j["error"])
                for url, (_url, data_j, _headers) in zip(urls, MockQueue.calls)
                if url.endswith("/result")
            ),
            {
                "node/jobs/restart/result": "Capability 'restart' not supported by node",
                "node/jobs/update/result": "Capability 'update' not supported by node",
                "node/jobs/auto-update/result": "Capability 'auto-update' not supported by node",
            },
        )
        self.assertEqual(len(urls), 5)
        self.assertEqual(self.node.restart_jobs, [])
        self.assertEqual(os.path.exists(self.state_path), False)
        self.assertEqual(MockOS.execs, [])

    def test_print_job_email_binie(self):
        self.node.node_printer = "Receipt"
        self.node.node_email_receivers = []
        result = self.node.print_job_email(
            dict(
                data_b64=colony_print.controllers.node.HELLO_WORLD_B64,
                name="hello_world",
                format="binie",
                options=dict(save_output=True, send_email=False),
            )
        )
        self.assertEqual(result["result"], "success")
        self.assertEqual(result["output_mime_type"], "application/pdf")
        self.assertEqual(base64.b64decode(result["output_data"])[:5], b"%PDF-")

        printer, data_b64, options = MockNPColony.calls[0]
        self.assertEqual(printer, "Receipt")
        self.assertEqual(options["media"], "RP80x297")
        self.assertEqual(options["scaling"], "none")
        self.assertEqual(options["output_path"].endswith(".pdf"), True)
        self.assertEqual(
            base64.b64decode(data_b64), base64.b64decode(result["output_data"])
        )

    def test_print_job_email_result(self):
        # the result of the job is posted to the server as JSON, so the
        # saved output must be a (base64 encoded) string and not bytes
        self.node.node_printer = "Receipt"
        self.node.node_email_receivers = []
        result = self.node.print_job_email(
            dict(
                data_b64=colony_print.controllers.node.HELLO_WORLD_B64,
                name="hello_world",
                format="binie",
                options=dict(save_output=True, send_email=False),
            )
        )
        result_j = json.loads(json.dumps(result))
        self.assertEqual(result_j, result)
        self.assertEqual(base64.b64decode(result_j["output_data"])[:5], b"%PDF-")

        result = self.node.print_job_email(
            dict(
                data_b64=colony_print.controllers.node.HELLO_WORLD_B64,
                name="hello_world",
                format="binie",
                options=dict(send_email=False),
            )
        )
        self.assertEqual(json.loads(json.dumps(result)), result)
        self.assertEqual(result["output_data"], None)

    def test_print_job_email_xmpl(self):
        self.node.node_printer = "Receipt"
        self.node.node_email_receivers = []
        result = self.node.print_job_email(
            dict(
                data_b64=self._xmpl(font_name="Colonia", fonts=[self._font()]),
                name="hello_world",
                format="xmpl",
                options=dict(save_output=True, send_email=False),
            )
        )
        self.assertEqual(result["result"], "success")
        output_data = base64.b64decode(result["output_data"])
        self.assertEqual(output_data[:5], b"%PDF-")
        self.assertEqual(b"Colonia" in output_data, True)

        printer, _data_b64, options = MockNPColony.calls[0]
        self.assertEqual(printer, "Receipt")
        self.assertEqual(options["media"], "RP80x297")
        self.assertEqual(len(self.node.font_cache.installed()), 1)

    def test_print_job_email_fonts(self):
        # the installation of fonts is not a document to be printed and
        # sent by email, the fonts are installed as in the normal mode
        self.node.node_mode = "email"
        data_b64 = base64.b64encode(
            json.dumps(dict(fonts=[self._font()])).encode("utf-8")
        )
        result = self.node.print_job(
            dict(data_b64=data_b64, name="fonts", type="fonts")
        )
        self.assertEqual(result["result"], "success")
        self.assertEqual(result["handler"], "fonts")
        self.assertEqual(result["data"]["fonts"][0]["name"], "Colonia")
        self.assertEqual(MockNPColony.calls, [])
        self.assertEqual(
            list(self.node.font_cache.files().keys()), [("colonia", "regular")]
        )

    def test_print_job_email_printer(self):
        # the printer of the node is a string of the environment, which is
        # a byte string (encoded as UTF-8 by the boot) in Python 2, that must
        # be usable together with the unicode strings of the job (eg: its
        # name, as decoded from the JSON of the server) when it's not ASCII
        printer = appier.legacy.u("Balcão")
        name = appier.legacy.u("Etiqueta São João")
        MockNPColony.format = "binie"
        self.node.node_printer = (
            printer if appier.legacy.PYTHON_3 else printer.encode("utf-8")
        )
        self.node.node_email_receivers = []
        result = self.node.print_job_email(
            dict(
                data_b64=colony_print.controllers.node.HELLO_WORLD_B64,
                name=name,
                options=dict(save_output=True, send_email=False),
            )
        )
        self.assertEqual(result["result"], "success")
        self.assertEqual(json.loads(json.dumps(result)), result)
        self.assertEqual(
            result["output_data"], colony_print.controllers.node.HELLO_WORLD_B64
        )

        # the name of the printer is given to npcolony as a string, the
        # same (byte) string of the environment in Python 2
        self.assertEqual(type(MockNPColony.calls[0][0]), str)
        self.assertEqual(MockNPColony.calls[0][0], self.node.node_printer)

    def test_print_job_email_commands(self):
        # the commands print no document, so they're handled as in the normal
        # mode (without any output document nor email), having no data
        self.node.node_mode = "email"
        self.node.node_restart = "exit"
        self.node.node_boot = True
        self.node.node_state = self.state_path
        result = self.node.print_job(dict(id="restart", name="restart", type="restart"))
        self.assertEqual(result, None)
        result = self.node.print_job(dict(id="update", name="update", type="update"))
        self.assertEqual(result, None)
        self.assertEqual(self.node.restart_jobs, ["restart", "update"])
        result = self.node.print_job(
            dict(
                id="auto-update",
                name="auto-update",
                type="auto-update",
                options=dict(enabled=False),
            )
        )
        self.assertEqual(
            result,
            dict(result="success", handler="auto-update", data=dict(auto=False)),
        )
        self.assertEqual(MockNPColony.calls, [])

    def test_restart(self):
        # the node only restarts when one of its jobs has requested it
        colony_print.node.sys = MockSys
        self.node.node_restart = "exit"
        self.assertEqual(self.node.restart(), dict())
        self.assertEqual(MockSys.exits, [])

        self.node.restart_jobs = ["first", "second"]
        self.assertRaises(MockInterrupt, self.node.restart)
        self.assertEqual(MockSys.exits, [colony_print.node.RESTART_CODE])
        self.assertEqual(self.node.restart_jobs, [])

    def test_restart_error(self):
        # a restart that fails (eg: the interpreter can't be run) results in
        # the error of every job that requested it and is not tried again
        colony_print.node.sys = MockSys
        colony_print.node.os = MockOS
        MockOS.error = OSError("Exec format error")
        self.node.node_restart = "exec"
        self.node.restart_jobs = ["first", "second"]
        results = self.node.restart()
        self.assertEqual(sorted(results.keys()), ["first", "second"])
        for result in results.values():
            self.assertEqual(result["result"], "error")
            self.assertEqual(result["error"], "Exec format error")
            self.assertEqual("OSError" in result["traceback"], True)
        self.assertEqual(json.loads(json.dumps(results)), results)
        self.assertEqual(self.node.restart_jobs, [])
        self.assertEqual(self.node.restart(), dict())
        self.assertEqual(MockSys.exits, [])

        # the same happens when the node is not able to restart (eg: its
        # restart was requested by a job before it was refused)
        self.node.node_restart = None
        self.node.restart_jobs = ["third"]
        results = self.node.restart()
        self.assertEqual(results["third"]["result"], "error")
        self.assertEqual(results["third"]["error"], "Restart 'None' not valid")

    def test_libraries(self):
        sys.modules["npcolony"] = MockLibrary
        sys.modules["gravo_pilot"] = MockLibrary
        self.assertEqual(
            self.node.libraries,
            {
                "npcolony": "1.0.0",
                "gravo_pilot": "1.0.0",
                "appier": appier.VERSION,
                "appier-extras": appier_extras.VERSION,
                "pillow": PIL.__version__,
                "reportlab": reportlab.Version,
            },
        )

    def test_libraries_not_installed(self):
        sys.modules["npcolony"] = None
        sys.modules["gravo_pilot"] = None
        libraries = self.node.libraries
        self.assertEqual(
            sorted(libraries.keys()), ["appier", "appier-extras", "pillow", "reportlab"]
        )
        self.assertEqual(libraries["appier"], appier.VERSION)

        sys.modules["gravo_pilot"] = MockLibrary
        libraries = self.node.libraries
        self.assertEqual("npcolony" in libraries, False)
        self.assertEqual(libraries["gravo_pilot"], "1.0.0")

    def test_libraries_no_version(self):
        libraries = self.node.libraries
        self.assertEqual("npcolony" in libraries, False)
        self.assertEqual("gravo_pilot" in libraries, False)
        self.assertEqual(libraries["pillow"], PIL.__version__)

        sys.modules["npcolony"] = MockNPColonyLegacy
        sys.modules["gravo_pilot"] = MockLibrary
        libraries = self.node.libraries
        self.assertEqual("npcolony" in libraries, False)
        self.assertEqual(libraries["gravo_pilot"], "1.0.0")

    def test_system(self):
        self.assertEqual(
            self.node.system,
            dict(
                name="Linux",
                release="6.8.0-45-generic",
                version="#45-Ubuntu SMP",
                machine="x86_64",
                architecture="%dbit" % (struct.calcsize("P") * 8),
            ),
        )
        self.assertEqual(self.node.system["architecture"] in ("32bit", "64bit"), True)

        MockPlatform.uname = ("Windows", "11", "10.0.22631", "ARM64")
        system = self.node.system
        self.assertEqual(system["name"], "Windows")
        self.assertEqual(system["release"], "11")
        self.assertEqual(system["version"], "10.0.22631")
        self.assertEqual(system["machine"], "ARM64")
        self.assertEqual("distribution" in system, False)

    def test_system_distribution(self):
        self._os_release(b'NAME="Ubuntu"\nPRETTY_NAME="Ubuntu 24.04.1 LTS"\n')
        system = self.node.system
        self.assertEqual(system["name"], "Linux")
        self.assertEqual(system["distribution"], "Ubuntu 24.04.1 LTS")

        self._os_release(b'NAME="Ubuntu"\nPRETTY_NAME=""\n')
        self.assertEqual("distribution" in self.node.system, False)

    def test_update(self):
        # only the nodes run by the boot know about their update
        self.assertEqual(self.node.update, None)

        self.node.node_boot = True
        self.assertEqual(self.node.update, dict(auto=True, status=None, time=None))

        appier.conf_s("NODE_UPDATE_STATUS", "skipped")
        appier.conf_s("NODE_UPDATE_TIME", "1790879619.9")
        try:
            self.node.node_update = False
            self.assertEqual(
                self.node.update, dict(auto=False, status="skipped", time=1790879619.9)
            )

            appier.conf_s("NODE_UPDATE_STATUS", "failure")
            appier.conf_s("NODE_UPDATE_ERROR", "Package update failed with code 1")
            update = self.node.update
            self.assertEqual(
                update,
                dict(
                    auto=False,
                    status="failure",
                    time=1790879619.9,
                    error="Package update failed with code 1",
                ),
            )
            self.assertEqual(json.loads(json.dumps(update)), update)

            appier.conf_s("NODE_UPDATE_ERROR", "")
            self.assertEqual("error" in self.node.update, False)
        finally:
            appier.conf_r("NODE_UPDATE_STATUS")
            appier.conf_r("NODE_UPDATE_TIME")
            appier.conf_r("NODE_UPDATE_ERROR")

    def test_capabilities(self):
        self.assertEqual(
            self.node.capabilities,
            [
                "npcolony",
                "gravo",
                "text",
                "binie",
                "xmpl",
                "pdf",
                "custom-paper",
                "dynamic-fonts",
                "gravo-extra-fonts",
                "gravo-record",
                "gravo-check-path",
            ],
        )

        # the printers don't report their custom paper sizes (an older
        # version of npcolony) or there are no printers to report them
        MockNPColony.devices = [
            dict(
                (key, value)
                for key, value in OFFICE_DEVICE.items()
                if not key == "custom"
            )
        ]
        self.assertEqual("custom-paper" in self.node.capabilities, False)
        MockNPColony.devices = []
        self.assertEqual("custom-paper" in self.node.capabilities, False)
        MockNPColony.devices = [dict(OFFICE_DEVICE, custom=None)]
        self.assertEqual("custom-paper" in self.node.capabilities, True)

        self.node.node_mode = "email"
        self.assertEqual(self.node.capabilities[-1], "email")

    def test_capabilities_windows(self):
        sys.modules["npcolony"] = MockNPColonyWindows
        sys.modules["gravo_pilot"] = None
        self.assertEqual(
            self.node.capabilities,
            ["npcolony", "text", "binie", "xmpl", "custom-paper", "dynamic-fonts"],
        )

        # the npcolony of the system doesn't report the loading of fonts
        # (eg: a build without the feature), so the fonts can't be installed
        MockNPColonyWindows.features = []
        self.assertEqual(
            self.node.capabilities,
            ["npcolony", "text", "binie", "xmpl", "custom-paper"],
        )

        sys.modules["npcolony"] = MockNPColonyLegacy
        self.assertEqual(
            self.node.capabilities,
            ["npcolony", "text", "binie", "xmpl", "custom-paper"],
        )

        sys.modules["npcolony"] = None
        self.assertEqual(self.node.capabilities, ["text"])

    def test_capabilities_control(self):
        # the node that is able to restart is restarted from the admin, the
        # one that is also run by the boot being updated from it as well
        sys.modules["npcolony"] = None
        sys.modules["gravo_pilot"] = None
        self.node.node_restart = "exec"
        self.assertEqual(self.node.capabilities, ["text", "restart"])

        self.node.node_boot = True
        self.assertEqual(
            self.node.capabilities, ["text", "restart", "update", "auto-update"]
        )

        self.node.node_mode = "email"
        self.node.node_restart = "exit"
        self.assertEqual(
            self.node.capabilities,
            ["text", "email", "restart", "update", "auto-update"],
        )

        # the update is a restart whose boot updates the node, so the node
        # that doesn't restart only has its auto-update set from the admin
        self.node.node_mode = "normal"
        self.node.node_restart = None
        self.assertEqual(self.node.capabilities, ["text", "auto-update"])

        # the remote control of the node disabled in its configuration
        self.node.node_restart = "exit"
        self.node.node_control = False
        self.assertEqual(self.node.capabilities, ["text"])

    def test_handle_job_title(self):
        data_b64 = base64.b64encode(b"%PDF-1.4 document").decode("utf-8")
        result = self.node._handle_job(
            dict(data_b64=data_b64, name="invoice", printer="office", format="pdf")
        )
        self.assertEqual(
            result,
            dict(result="success", handler="npcolony", printer="office", data=dict()),
        )
        self.assertEqual(
            MockNPColony.calls, [("office", data_b64, dict(title="invoice"))]
        )

    def test_handle_job_printer(self):
        # the printer of the node, a byte string (encoded as UTF-8 by the
        # boot) in Python 2, is used by the jobs that don't select one, whose
        # strings are unicode ones (decoded from the JSON of the server), the
        # printer of the result being an unicode string (JSON serializable)
        # and the one given to npcolony the string of the environment
        printer = appier.legacy.u("Balcão")
        printer_s = printer if appier.legacy.PYTHON_3 else printer.encode("utf-8")
        name = appier.legacy.u("Etiqueta São João")
        data_b64 = base64.b64encode(b"%PDF-1.4 document").decode("utf-8")
        self.node.node_printer = printer_s
        result = self.node._handle_job(dict(data_b64=data_b64, name=name, format="pdf"))
        self.assertEqual(
            result,
            dict(result="success", handler="npcolony", printer=printer, data=dict()),
        )
        self.assertEqual(json.loads(json.dumps(result)), result)
        self.assertEqual(MockNPColony.calls, [(printer_s, data_b64, dict(title=name))])
        self.assertEqual(type(MockNPColony.calls[0][0]), str)

        # the printer selected by a job (an unicode string) is handled the
        # same way, taking precedence over the printer of the node
        self.node.node_printer = "Receipt"
        MockNPColony.calls = []
        result = self.node._handle_job(
            dict(data_b64=data_b64, name=name, printer=printer, format="pdf")
        )
        self.assertEqual(result["printer"], printer)
        self.assertEqual(MockNPColony.calls, [(printer_s, data_b64, dict(title=name))])
        self.assertEqual(type(MockNPColony.calls[0][0]), str)

    def test_handle_job_type(self):
        data_b64 = base64.b64encode(b"Hello World").decode("utf-8")
        result = self.node._handle_job(
            dict(data_b64=data_b64, name="hello", type="text")
        )
        self.assertEqual(result["result"], "success")
        self.assertEqual(result["handler"], "text")

        # a job of a type that is not handled by the node is not printed,
        # so it must fail instead of being reported as a finished job
        self.assertRaises(
            appier.OperationalError,
            lambda: self.node._handle_job(
                dict(data_b64=data_b64, name="hello", type="Text")
            ),
        )

        self.node.node_mode = "normal"
        self.assertRaises(
            appier.OperationalError,
            lambda: self.node.print_job(
                dict(data_b64=data_b64, name="hello", type="zpl")
            ),
        )
        self.assertEqual(MockNPColony.calls, [])
        self.assertEqual(MockGravostyleAPI.calls, [])

    def test_handle_job_fonts(self):
        fonts = [self._font(), self._font(name="Binaria", style="regular")]
        data_b64 = base64.b64encode(json.dumps(dict(fonts=fonts)).encode("utf-8"))
        result = self.node._handle_job(
            dict(data_b64=data_b64, name="fonts", type="fonts")
        )
        self.assertEqual(result["result"], "success")
        self.assertEqual(result["handler"], "fonts")
        self.assertEqual(
            [(font["name"], font["md5"]) for font in result["data"]["fonts"]],
            [
                ("Colonia", hashlib.md5(build_font()).hexdigest()),
                ("Binaria", hashlib.md5(build_font("Binaria")).hexdigest()),
            ],
        )
        self.assertEqual(MockNPColony.calls, [])
        self.assertEqual(
            sorted(self.node.font_cache.files().keys()),
            [("binaria", "regular"), ("colonia", "regular")],
        )

    def test_handle_job_xmpl(self):
        result = self.node._handle_job(
            dict(
                data_b64=self._xmpl(font_name="Colonia"),
                name="hello_world",
                printer="Receipt",
                format="xmpl",
                fonts=[self._font()],
            )
        )
        self.assertEqual(result["result"], "success")
        printer, data_b64, options = MockNPColony.calls[0]
        self.assertEqual(printer, "Receipt")
        self.assertEqual(base64.b64decode(data_b64)[:5], b"%PDF-")
        self.assertEqual(b"Colonia" in base64.b64decode(data_b64), True)
        self.assertEqual(
            options, dict(title="hello_world", media="RP80x297", scaling="none")
        )

    def test_handle_job_commands(self):
        # the jobs that restart the node (commands without data) only request
        # its restart, having no result (the node is restarted afterwards)
        self.node.node_restart = "exec"
        self.node.node_boot = True
        self.node.node_state = self.state_path
        result = self.node._handle_job(dict(id="first", name="restart", type="restart"))
        self.assertEqual(result, None)
        self.assertEqual(self.node.restart_jobs, ["first"])
        self.assertEqual(os.path.exists(self.state_path), False)

        result = self.node._handle_job(dict(id="second", name="update", type="update"))
        self.assertEqual(result, None)
        self.assertEqual(self.node.restart_jobs, ["first", "second"])
        self.assertEqual(self._state(), b"NODE_UPDATE_ONCE=1\r\n")

        # the auto-update is set without any restart, with the result of
        # any other job
        result = self.node._handle_job(
            dict(
                id="third",
                name="auto-update",
                type="auto-update",
                options=dict(enabled=True),
            )
        )
        self.assertEqual(
            result, dict(result="success", handler="auto-update", data=dict(auto=True))
        )
        self.assertEqual(json.loads(json.dumps(result)), result)
        self.assertEqual(self.node.restart_jobs, ["first", "second"])
        self.assertEqual(MockNPColony.calls, [])

    def test_handle_npcolony_binie(self):
        self.node._handle_npcolony(
            colony_print.controllers.node.HELLO_WORLD_B64,
            format="binie",
            printer="Receipt",
            options=dict(title="hello_world"),
        )
        printer, data_b64, options = MockNPColony.calls[0]
        self.assertEqual(printer, "Receipt")
        self.assertEqual(base64.b64decode(data_b64)[:5], b"%PDF-")
        self.assertEqual(
            options, dict(title="hello_world", media="RP80x297", scaling="none")
        )
        self.assertEqual(self._media_box(data_b64), (0.0, 0.0, 226.77, 841.89))

    def test_handle_npcolony_binie_detected(self):
        self.node._handle_npcolony(
            colony_print.controllers.node.HELLO_WORLD_B64, printer="default"
        )
        printer, data_b64, options = MockNPColony.calls[0]
        self.assertEqual(printer, "default")
        self.assertEqual(base64.b64decode(data_b64)[:5], b"%PDF-")
        self.assertEqual(options, dict(media="A4", scaling="none"))
        self.assertEqual(self._media_box(data_b64), (0.0, 0.0, 595.28, 841.89))

    def test_handle_npcolony_binie_invalid(self):
        data_b64 = base64.b64encode(b"%PDF-1.4 document").decode("utf-8")
        self.assertRaises(
            colony_print.InvalidBinie,
            lambda: self.node._handle_npcolony(
                data_b64, format="binie", printer="Receipt"
            ),
        )
        self.assertEqual(MockNPColony.calls, [])

    def test_handle_npcolony_default(self):
        self.node._handle_npcolony(
            colony_print.controllers.node.HELLO_WORLD_B64, format="binie"
        )
        printer, data_b64, options = MockNPColony.calls[0]
        self.assertEqual(printer, None)
        self.assertEqual(base64.b64decode(data_b64)[:5], b"%PDF-")
        self.assertEqual(options, dict())

    def test_handle_npcolony_pdf(self):
        data_b64 = base64.b64encode(b"%PDF-1.4 document").decode("utf-8")
        self.node._handle_npcolony(
            data_b64,
            format="pdf",
            printer="Receipt",
            options=dict(media="Custom.80x200mm", scaling="fit"),
        )
        self.assertEqual(
            MockNPColony.calls,
            [("Receipt", data_b64, dict(media="Custom.80x200mm", scaling="fit"))],
        )

    def test_handle_npcolony_raw(self):
        data_b64 = base64.b64encode(b"raw printer data").decode("utf-8")
        self.node._handle_npcolony(data_b64, printer="Receipt")
        self.assertEqual(MockNPColony.calls, [("Receipt", data_b64, dict())])

    def test_handle_npcolony_printer(self):
        # npcolony only accepts the unicode strings that are ASCII in Python
        # 2, so the name of the printer is given to it as a string (encoded
        # as UTF-8 in Python 2), while its device (whose name is an unicode
        # string) is the one used in the conversion of the binie document
        printer = appier.legacy.u("Balcão")
        printer_s = printer if appier.legacy.PYTHON_3 else printer.encode("utf-8")
        MockNPColony.devices = [dict(RECEIPT_DEVICE, name=printer), OFFICE_DEVICE]
        self.node._handle_npcolony(
            colony_print.controllers.node.HELLO_WORLD_B64,
            format="binie",
            printer=printer,
        )
        name, data_b64, options = MockNPColony.calls[0]
        self.assertEqual(type(name), str)
        self.assertEqual(name, printer_s)
        self.assertEqual(base64.b64decode(data_b64)[:5], b"%PDF-")
        self.assertEqual(options, dict(media="RP80x297", scaling="none"))

        # the string of the environment is given to npcolony untouched and
        # no printer selects the default one (no printer given to npcolony)
        MockNPColony.calls = []
        data_b64 = base64.b64encode(b"raw printer data").decode("utf-8")
        self.node._handle_npcolony(data_b64, printer=printer_s)
        self.node._handle_npcolony(data_b64, printer="")
        self.assertEqual(
            MockNPColony.calls,
            [(printer_s, data_b64, dict()), (None, data_b64, dict())],
        )

    def test_handle_npcolony_binie_system(self):
        MockNPColony.format = "binie"
        self.node._handle_npcolony(
            colony_print.controllers.node.HELLO_WORLD_B64,
            format="binie",
            printer="Receipt",
        )
        self.assertEqual(
            MockNPColony.calls,
            [("Receipt", colony_print.controllers.node.HELLO_WORLD_B64, dict())],
        )

    def test_handle_npcolony_invalid_format(self):
        self.assertRaises(
            appier.OperationalError,
            lambda: self.node._handle_npcolony(
                colony_print.controllers.node.HELLO_WORLD_B64,
                format="zpl",
                printer="Receipt",
            ),
        )
        self.assertEqual(MockNPColony.calls, [])

    def test_handle_npcolony_fonts(self):
        self.node._handle_npcolony(
            COLONIA_B64, format="binie", printer="Receipt", fonts=[self._font()]
        )
        printer, data_b64, options = MockNPColony.calls[0]
        self.assertEqual(printer, "Receipt")
        self.assertEqual(b"Colonia" in base64.b64decode(data_b64), True)
        self.assertEqual(options, dict(media="RP80x297", scaling="none"))

        # the installed font is used by the documents of the jobs that don't
        # provide it, as the fonts of the system are (no substitution)
        self.node._handle_npcolony(COLONIA_B64, format="binie", printer="Receipt")
        _printer, data_b64, _options = MockNPColony.calls[1]
        self.assertEqual(b"Colonia" in base64.b64decode(data_b64), True)

        # the same font referenced by its MD5 (no data) is the one used
        md5 = hashlib.md5(build_font()).hexdigest()
        self.node._handle_npcolony(
            COLONIA_B64, format="binie", fonts=[dict(name="Colonia", md5=md5)]
        )
        self.assertEqual(len(MockNPColony.calls), 3)
        self.assertEqual(len(self.node.font_cache.installed()), 1)

    def test_handle_npcolony_fonts_windows(self):
        sys.modules["npcolony"] = MockNPColonyWindows
        self.node._handle_npcolony(
            COLONIA_B64, format="binie", printer="Receipt", fonts=[self._font()]
        )
        path = os.path.join(
            self.fonts_dir, "%s.ttf" % hashlib.md5(build_font()).hexdigest()
        )
        self.assertEqual(MockNPColonyWindows.fonts, [("load", path)])
        self.assertEqual(MockNPColonyWindows.calls, [("Receipt", COLONIA_B64, dict())])

        # a job with the same (already loaded) font doesn't load it again
        self.node._handle_npcolony(
            COLONIA_B64, format="binie", printer="Receipt", fonts=[self._font()]
        )
        self.assertEqual(MockNPColonyWindows.fonts, [("load", path)])
        self.assertEqual(len(MockNPColonyWindows.calls), 2)

    def test_handle_npcolony_fonts_invalid(self):
        self.assertRaises(
            appier.OperationalError,
            lambda: self.node._handle_npcolony(
                COLONIA_B64,
                format="binie",
                printer="Receipt",
                fonts=[self._font(), dict(name="Binaria", md5="0" * 32)],
            ),
        )
        self.assertRaises(
            appier.OperationalError,
            lambda: self.node._handle_npcolony(
                COLONIA_B64,
                format="binie",
                printer="Receipt",
                fonts=[dict(name="Calibri", data_b64=self._font()["data_b64"])],
            ),
        )
        self.assertEqual(MockNPColony.calls, [])

        # the npcolony of the system is not able to load the fonts
        sys.modules["npcolony"] = MockNPColonyLegacy
        self.assertRaises(
            appier.OperationalError,
            lambda: self.node._handle_npcolony(
                COLONIA_B64, format="binie", fonts=[self._font()]
            ),
        )

    def test_handle_npcolony_xmpl(self):
        self.node._handle_npcolony(
            self._xmpl(font_name="Colonia", fonts=[self._font()]),
            format="xmpl",
            printer="Receipt",
        )
        printer, data_b64, options = MockNPColony.calls[0]
        self.assertEqual(printer, "Receipt")
        self.assertEqual(b"Colonia" in base64.b64decode(data_b64), True)
        self.assertEqual(options, dict(media="RP80x297", scaling="none"))

        # prints a document declaring another font on windows, where the
        # installed fonts are loaded in the system (GDI) for the printing
        sys.modules["npcolony"] = MockNPColonyWindows
        self.node._handle_npcolony(
            self._xmpl(fonts=[self._font(name="Binaria")]),
            format="xmpl",
            printer="Receipt",
        )
        printer, data_b64, options = MockNPColonyWindows.calls[0]
        self.assertEqual(printer, "Receipt")
        self.assertEqual(self._hello_world(data_b64), True)
        self.assertEqual(options, dict())
        self.assertEqual(
            sorted(MockNPColonyWindows.fonts),
            sorted(("load", path) for path in self.node.font_cache.files().values()),
        )
        self.assertEqual(len(MockNPColonyWindows.fonts), 2)

        self.assertRaises(
            Exception,
            lambda: self.node._handle_npcolony(
                base64.b64encode(b"<printing_document>"), format="xmpl"
            ),
        )
        data = b'<printing_document name="logo"><image path="/etc/passwd"/></printing_document>'
        self.assertRaises(
            appier.OperationalError,
            lambda: self.node._handle_npcolony(base64.b64encode(data), format="xmpl"),
        )
        self.assertEqual(len(MockNPColonyWindows.calls), 1)

    def test_is_binie(self):
        binie_b64 = colony_print.controllers.node.HELLO_WORLD_B64
        pdf_b64 = base64.b64encode(b"%PDF-1.4 document").decode("utf-8")
        self.assertEqual(self.node._is_binie(binie_b64), True)
        self.assertEqual(self.node._is_binie(binie_b64, format="binie"), True)
        self.assertEqual(self.node._is_binie(binie_b64, format="pdf"), False)
        self.assertEqual(self.node._is_binie(pdf_b64), False)
        self.assertEqual(self.node._is_binie(pdf_b64, format="binie"), True)
        self.assertEqual(self.node._is_binie("not base64 data"), False)

        data = base64.b64decode(binie_b64)
        data = data[:264] + struct.pack("<I", 2) + data[268:] + struct.pack("<II", 3, 0)
        self.assertEqual(
            self.node._is_binie(base64.b64encode(data).decode("utf-8")), True
        )

        MockNPColony.format = "binie"
        self.assertEqual(self.node._is_binie(binie_b64), False)
        self.assertEqual(self.node._is_binie(binie_b64, format="binie"), False)

        sys.modules["npcolony"] = MockNPColonyLegacy
        self.assertEqual(self.node._is_binie(binie_b64, format="binie"), False)

    def test_convert_binie(self):
        data_b64, options = self.node._convert_binie(
            colony_print.controllers.node.HELLO_WORLD_B64,
            printer="receipt",
            options=dict(title="hello_world", media="Custom.80x200mm", scaling="fit"),
        )
        self.assertEqual(base64.b64decode(data_b64)[:5], b"%PDF-")
        self.assertEqual(
            options, dict(title="hello_world", media="RP80x297", scaling="fit")
        )
        self.assertEqual(self._media_box(data_b64), (0.0, 0.0, 226.77, 841.89))

    def test_convert_binie_document_size(self):
        data = base64.b64decode(colony_print.controllers.node.HELLO_WORLD_B64)
        data = data[:256] + struct.pack("<II", 800, 1000) + data[264:]
        data_b64, options = self.node._convert_binie(
            base64.b64encode(data).decode("utf-8"),
            printer="Receipt",
            options=dict(media="A4"),
        )
        self.assertEqual(options, dict(media="Custom.80x100mm", scaling="none"))
        media_box = self._media_box(data_b64)
        self.assertAlmostEqual(media_box[2], 226.77, places=2)
        self.assertAlmostEqual(media_box[3], 283.46, places=2)

        data = data[:256] + struct.pack("<II", 1500, 2000) + data[264:]
        data_b64, options = self.node._convert_binie(
            base64.b64encode(data).decode("utf-8"), printer="office"
        )
        self.assertEqual(options, dict(media="Custom.150x200mm", scaling="none"))
        media_box = self._media_box(data_b64)
        self.assertAlmostEqual(media_box[2], 425.2, places=2)
        self.assertAlmostEqual(media_box[3], 566.93, places=2)

    def test_convert_binie_document_size_margins(self):
        MockNPColony.devices = [
            dict(
                OFFICE_DEVICE,
                custom=dict(OFFICE_DEVICE["custom"], margin_left=0.0, margin_top=0.0),
            )
        ]
        data = base64.b64decode(colony_print.controllers.node.HELLO_WORLD_B64)
        data = data[:256] + struct.pack("<II", 1500, 2000) + data[264:]
        data_b64, _options = self.node._convert_binie(
            base64.b64encode(data).decode("utf-8")
        )
        renderer = colony_print.BinieRenderer(margins=(0.0, 12.0, 12.0, 0.0))
        file = appier.legacy.BytesIO()
        renderer.render(data, file)
        self.assertEqual(
            self._contents(data_b64),
            self._contents(base64.b64encode(file.getvalue())),
        )

    def test_convert_binie_document_size_media(self):
        data_b64, options = self.node._convert_binie(
            LABEL_B64, printer="office", options=dict(title="label")
        )
        self.assertEqual(options, dict(title="label", media="A4", scaling="none"))
        self.assertEqual(self._media_box(data_b64), (0.0, 0.0, 595.28, 841.89))
        self.assertEqual(self._pages(data_b64), 1)

        renderer = colony_print.BinieRenderer(
            size=(595.28, 841.89), margins=(12.0, 12.0, 12.0, 12.0), custom=False
        )
        file = appier.legacy.BytesIO()
        renderer.render(base64.b64decode(LABEL_B64), file)
        self.assertEqual(
            self._contents(data_b64),
            self._contents(base64.b64encode(file.getvalue())),
        )

        MockNPColony.devices = [dict(OFFICE_DEVICE, custom=None)]
        data_b64, options = self.node._convert_binie(LABEL_B64, printer="office")
        self.assertEqual(options, dict(media="A4", scaling="none"))
        self.assertEqual(self._media_box(data_b64), (0.0, 0.0, 595.28, 841.89))
        self.assertEqual(self._pages(data_b64), 1)

    def test_convert_binie_document_size_default(self):
        data = base64.b64decode(colony_print.controllers.node.HELLO_WORLD_B64)
        data = data[:256] + struct.pack("<II", 800, 2970) + data[264:]
        data_b64, options = self.node._convert_binie(
            base64.b64encode(data).decode("utf-8"), printer="Receipt"
        )
        self.assertEqual(options, dict(media="RP80x297", scaling="none"))
        self.assertEqual(self._media_box(data_b64), (0.0, 0.0, 226.77, 841.89))

    def test_convert_binie_document_size_legacy(self):
        MockNPColony.devices = [
            dict(
                (key, value)
                for key, value in RECEIPT_DEVICE.items()
                if not key == "custom"
            )
        ]
        data = base64.b64decode(colony_print.controllers.node.HELLO_WORLD_B64)
        data = data[:256] + struct.pack("<II", 800, 1000) + data[264:]
        data_b64, options = self.node._convert_binie(
            base64.b64encode(data).decode("utf-8"), printer="Receipt"
        )
        self.assertEqual(options, dict(media="RP80x297", scaling="none"))
        self.assertEqual(self._media_box(data_b64), (0.0, 0.0, 226.77, 841.89))

        MockNPColony.devices = [
            dict(
                name="label",
                is_default=True,
                media="w227h23",
                width=226.77,
                length=22.68,
                left=0.0,
                bottom=0.0,
                right=226.77,
                top=22.68,
            )
        ]
        data_b64, options = self.node._convert_binie(LABEL_B64)
        self.assertEqual(options, dict(media="w227h23", scaling="none"))
        self.assertEqual(self._media_box(data_b64), (0.0, 0.0, 226.77, 22.68))
        self.assertEqual(self._pages(data_b64), 1)

    def test_convert_binie_document_size_no_device(self):
        MockNPColony.devices = []
        data_b64, options = self.node._convert_binie(
            LABEL_B64, printer="missing", options=dict(media="A4")
        )
        self.assertEqual(options, dict(media="Custom.80x8mm", scaling="none"))
        media_box = self._media_box(data_b64)
        self.assertAlmostEqual(media_box[2], 226.77, places=2)
        self.assertAlmostEqual(media_box[3], 22.68, places=2)

    def test_convert_binie_no_device(self):
        MockNPColony.devices = []
        data_b64, options = self.node._convert_binie(
            colony_print.controllers.node.HELLO_WORLD_B64,
            printer="missing",
            options=dict(media="Custom.80x200mm"),
        )
        self.assertEqual(options, dict(scaling="none"))
        media_box = self._media_box(data_b64)
        self.assertAlmostEqual(media_box[2], 595.28, places=2)
        self.assertAlmostEqual(media_box[3], 841.89, places=2)

    def test_convert_binie_legacy_device(self):
        MockNPColony.devices = [
            dict(
                name="legacy", is_default=True, media="A5", width=419.53, length=595.28
            )
        ]
        data_b64, options = self.node._convert_binie(
            colony_print.controllers.node.HELLO_WORLD_B64
        )
        self.assertEqual(options, dict(media="A5", scaling="none"))
        self.assertEqual(self._media_box(data_b64), (0.0, 0.0, 419.53, 595.28))

    def test_convert_binie_fonts(self):
        self.node.font_cache.install(self._font())
        data_b64, _options = self.node._convert_binie(COLONIA_B64, printer="Receipt")
        self.assertEqual(b"Colonia" in base64.b64decode(data_b64), True)

        self.node.font_cache = None
        data_b64, _options = self.node._convert_binie(
            colony_print.controllers.node.HELLO_WORLD_B64, printer="Receipt"
        )
        self.assertEqual(base64.b64decode(data_b64)[:5], b"%PDF-")

    def test_device(self):
        self.assertEqual(self.node._device("Receipt"), RECEIPT_DEVICE)
        self.assertEqual(self.node._device("receipt"), RECEIPT_DEVICE)
        self.assertEqual(self.node._device("office"), OFFICE_DEVICE)
        self.assertEqual(self.node._device("default"), OFFICE_DEVICE)
        self.assertEqual(self.node._device(""), OFFICE_DEVICE)
        self.assertEqual(self.node._device(None), OFFICE_DEVICE)
        self.assertEqual(self.node._device("missing"), dict())

        MockNPColony.devices = [RECEIPT_DEVICE, dict(OFFICE_DEVICE, is_default=False)]
        self.assertEqual(self.node._device("default"), dict())

        MockNPColony.devices = [RECEIPT_DEVICE]
        self.assertEqual(self.node._device("default"), RECEIPT_DEVICE)

        MockNPColony.devices = []
        self.assertEqual(self.node._device("default"), dict())

    def test_is_custom(self):
        is_custom = self.node._is_custom
        self.assertEqual(is_custom(RECEIPT_DEVICE, (226.77, 283.46)), True)
        self.assertEqual(is_custom(RECEIPT_DEVICE, (226.77, 841.89)), False)
        self.assertEqual(is_custom(RECEIPT_DEVICE, (283.46, 283.46)), False)
        self.assertEqual(is_custom(RECEIPT_DEVICE, (226.77, 22.68)), False)

        self.assertEqual(is_custom(OFFICE_DEVICE, (425.2, 566.93)), True)
        self.assertEqual(is_custom(OFFICE_DEVICE, (226.77, 22.68)), False)
        self.assertEqual(is_custom(OFFICE_DEVICE, (595.28, 841.89)), False)
        self.assertEqual(is_custom(OFFICE_DEVICE, (597.28, 843.89)), False)
        self.assertEqual(is_custom(OFFICE_DEVICE, (599.28, 841.89)), True)
        self.assertEqual(is_custom(OFFICE_DEVICE, (278.99, 419.5)), True)
        self.assertEqual(is_custom(OFFICE_DEVICE, (277.0, 417.5)), True)
        self.assertEqual(is_custom(OFFICE_DEVICE, (275.0, 419.5)), False)
        self.assertEqual(is_custom(OFFICE_DEVICE, (612.0, 1008.0)), True)
        self.assertEqual(is_custom(OFFICE_DEVICE, (614.0, 1010.0)), True)
        self.assertEqual(is_custom(OFFICE_DEVICE, (615.0, 1008.0)), False)
        self.assertEqual(is_custom(OFFICE_DEVICE, (425.2, 1011.0)), False)

        custom = dict(RECEIPT_DEVICE["custom"], max_width=226.77)
        device = dict(RECEIPT_DEVICE, custom=custom)
        self.assertEqual(is_custom(device, (800 / 254.0 * 72.0, 283.46)), True)

        device = dict(OFFICE_DEVICE, custom=None)
        self.assertEqual(is_custom(device, (425.2, 566.93)), False)

        device = dict(name="legacy", media="A4", width=595.28, length=841.89)
        self.assertEqual(is_custom(device, (425.2, 566.93)), False)

    def test_convert_xmpl(self):
        data_b64, fonts = self.node._convert_xmpl(self._xmpl())
        self.assertEqual(self._hello_world(data_b64), True)
        self.assertEqual(fonts, [])

        url = "https://fonts.hive.pt/colonia.ttf"
        data_b64, fonts = self.node._convert_xmpl(
            self._xmpl(fonts=[dict(name="Colonia", url=url)]),
            fonts=[dict(name="Binaria", md5="0" * 32)],
        )
        self.assertEqual(self._hello_world(data_b64), True)
        self.assertEqual(
            fonts,
            [dict(name="Colonia", url=url), dict(name="Binaria", md5="0" * 32)],
        )

        self.assertRaises(
            Exception,
            lambda: self.node._convert_xmpl(base64.b64encode(b"not a document")),
        )

        # an image read from the file system of the node is refused (as the
        # server may not have verified the document), only inline images
        data = b'<printing_document name="logo"><image path="/etc/passwd"/></printing_document>'
        self.assertRaises(
            appier.OperationalError,
            lambda: self.node._convert_xmpl(base64.b64encode(data)),
        )

    def test_handle_gravo_forwards_check_path(self):
        self.node._handle_gravo(self._gravo_payload(check_path=True, dry_run=True))
        self.assertEqual(len(MockGravostyleAPI.calls), 1)
        self.assertEqual(MockGravostyleAPI.calls[0]["check_path"], True)

    def test_handle_gravo_check_path_defaults_to_false(self):
        self.node._handle_gravo(self._gravo_payload(dry_run=True))
        self.assertEqual(len(MockGravostyleAPI.calls), 1)
        self.assertEqual(MockGravostyleAPI.calls[0]["check_path"], False)

    def test_stage_extra_fonts_writes_payloads(self):
        payload_a = b"\x00\x01\x00\x00font-a-payload"
        payload_b = b"\x00\x01\x00\x00font-b-payload"
        extra_fonts = dict(
            font_a=base64.b64encode(payload_a),
            font_b=base64.b64encode(payload_b),
        )
        paths = self.node._stage_extra_fonts(extra_fonts, self.target_dir)
        self.assertEqual(
            sorted(paths.keys()),
            ["font_a", "font_b"],
        )
        self.assertEqual(paths["font_a"], os.path.join(self.target_dir, "font_a.f3s"))
        self.assertEqual(paths["font_b"], os.path.join(self.target_dir, "font_b.f3s"))
        with open(paths["font_a"], "rb") as file:
            self.assertEqual(file.read(), payload_a)
        with open(paths["font_b"], "rb") as file:
            self.assertEqual(file.read(), payload_b)

    def test_stage_extra_fonts_empty_mapping(self):
        paths = self.node._stage_extra_fonts({}, self.target_dir)
        self.assertEqual(paths, {})
        self.assertEqual(os.listdir(self.target_dir), [])

    def test_stage_extra_fonts_overrides_existing(self):
        existing_path = os.path.join(self.target_dir, "font_a.f3s")
        with open(existing_path, "wb") as file:
            file.write(b"stale")
        payload = b"\x00\x01\x00\x00fresh-payload"
        paths = self.node._stage_extra_fonts(
            dict(font_a=base64.b64encode(payload)), self.target_dir
        )
        with open(paths["font_a"], "rb") as file:
            self.assertEqual(file.read(), payload)

    def test_decode_payload_json(self):
        data = json.dumps(dict(text="Hello World", font="HELVETICA 1L"))
        data_b64 = base64.b64encode(data.encode("utf-8"))
        payload = self.node._decode_payload(data_b64)
        self.assertEqual(payload, dict(text="Hello World", font="HELVETICA 1L"))

    def test_decode_payload_unicode(self):
        original = dict(text=appier.legacy.u("é✨"))
        data_b64 = base64.b64encode(json.dumps(original).encode("utf-8"))
        payload = self.node._decode_payload(data_b64)
        self.assertEqual(payload, original)

    def test_decode_payload_multifont(self):
        data = json.dumps(dict(text=[["HELVETICA 1L", "A"], ["TIMES 1L", "B"]]))
        data_b64 = base64.b64encode(data.encode("utf-8"))
        payload = self.node._decode_payload(data_b64)
        self.assertEqual(payload, dict(text=[["HELVETICA 1L", "A"], ["TIMES 1L", "B"]]))

    def test_decode_payload_invalid(self):
        data_b64 = base64.b64encode(b"not a json payload")
        self.assertRaises(ValueError, lambda: self.node._decode_payload(data_b64))

    def test_handle_fonts(self):
        data_b64 = base64.b64encode(
            json.dumps(dict(fonts=[self._font()])).encode("utf-8")
        )
        result = self.node._handle_fonts(data_b64)
        self.assertEqual(len(result["fonts"]), 1)
        self.assertEqual(result["fonts"][0]["name"], "Colonia")
        self.assertEqual(
            result["fonts"][0]["md5"], hashlib.md5(build_font()).hexdigest()
        )

        sys.modules["npcolony"] = MockNPColonyLegacy
        self.assertRaises(
            appier.OperationalError, lambda: self.node._handle_fonts(data_b64)
        )

    def test_handle_restart(self):
        self.node.node_restart = "exec"
        self.node._handle_restart("first")
        self.assertEqual(self.node.restart_jobs, ["first"])

        # the node that is not run by the boot is not able to update itself
        self.assertRaises(
            appier.OperationalError,
            lambda: self.node._handle_restart("second", update=True),
        )
        self.assertEqual(self.node.restart_jobs, ["first"])

        # the boot is told to update the packages of the node (once) by
        # the state file, that keeps its other values
        self.node.node_boot = True
        self.node.node_state = self.state_path
        with open(self.state_path, "wb") as file:
            file.write(b"NODE_UPDATE=0\r\n")
        self.node._handle_restart("second", update=True)
        self.assertEqual(self.node.restart_jobs, ["first", "second"])
        self.assertEqual(self._state(), b"NODE_UPDATE=0\r\nNODE_UPDATE_ONCE=1\r\n")

        # the restart is not requested when the state file can't be saved
        # (eg: a directory in its place), as the node would not be updated
        self.node.node_state = self.target_dir
        self.assertRaises(
            Exception, lambda: self.node._handle_restart("third", update=True)
        )
        self.assertEqual(self.node.restart_jobs, ["first", "second"])

        # the node that is not able to restart (or whose remote control is
        # disabled) refuses the restart, even when requested by the server
        self.node.node_state = self.state_path
        self.node.node_restart = None
        for update in (False, True):
            self.assertRaises(
                appier.OperationalError,
                lambda: self.node._handle_restart("third", update=update),
            )
        self.node.node_restart = "exit"
        self.node.node_control = False
        for update in (False, True):
            self.assertRaises(
                appier.OperationalError,
                lambda: self.node._handle_restart("third", update=update),
            )
        self.assertEqual(self.node.restart_jobs, ["first", "second"])

    def test_handle_auto_update(self):
        # the node that is not run by the boot has no auto-update
        self.assertRaises(
            appier.OperationalError,
            lambda: self.node._handle_auto_update(dict(enabled=False)),
        )
        self.assertEqual(os.path.exists(self.state_path), False)

        self.node.node_boot = True
        self.node.node_state = self.state_path
        result = self.node._handle_auto_update(dict(enabled=False))
        self.assertEqual(result, dict(auto=False))
        self.assertEqual(self.node.node_update, False)
        self.assertEqual(self.node.update["auto"], False)
        self.assertEqual(self._state(), b"NODE_UPDATE=0\r\n")

        # the other values of the state file are kept (eg: an update that
        # was requested and not yet run by the boot)
        with open(self.state_path, "wb") as file:
            file.write(b"NODE_UPDATE=0\r\nNODE_UPDATE_ONCE=1\r\n")
        result = self.node._handle_auto_update(dict(enabled=True))
        self.assertEqual(result, dict(auto=True))
        self.assertEqual(self.node.node_update, True)
        self.assertEqual(self._state(), b"NODE_UPDATE=1\r\nNODE_UPDATE_ONCE=1\r\n")

        # the auto-update must be explicitly set (as a boolean value)
        for options in (dict(), dict(enabled=None), dict(enabled="0"), dict(enabled=0)):
            self.assertRaises(
                appier.AssertionError,
                lambda: self.node._handle_auto_update(options),
            )
        self.assertEqual(self.node.node_update, True)
        self.assertEqual(self._state(), b"NODE_UPDATE=1\r\nNODE_UPDATE_ONCE=1\r\n")

        # the auto-update of the node is not changed when the state file
        # can't be saved (eg: a directory in its place)
        self.node.node_state = self.target_dir
        self.assertRaises(
            Exception, lambda: self.node._handle_auto_update(dict(enabled=False))
        )
        self.assertEqual(self.node.node_update, True)

        self.node.node_state = self.state_path
        self.node.node_control = False
        self.assertRaises(
            appier.OperationalError,
            lambda: self.node._handle_auto_update(dict(enabled=False)),
        )

    def test_build_font_cache(self):
        self.node.font_cache.install(self._font())
        appier.conf_s("FONTS_PATH", self.fonts_dir)
        appier.conf_s("FONT_MAX_SIZE", "1024")
        try:
            font_cache = self.node._build_font_cache()
        finally:
            appier.conf_r("FONTS_PATH")
            appier.conf_r("FONT_MAX_SIZE")
        self.assertEqual(font_cache.path, self.fonts_dir)
        self.assertEqual(font_cache.max_size, 1024)
        self.assertEqual(font_cache.installed(), self.node.font_cache.installed())

        font_cache = self.node._build_font_cache()
        self.assertEqual(
            font_cache.path, os.path.expanduser(colony_print.node.FONTS_PATH)
        )
        self.assertEqual(font_cache.max_size, colony_print.FONT_MAX_SIZE)

        # a windows node (service) without the path configured keeps the
        # fonts in its data directory (the one with its configuration)
        with open(os.path.join(self.target_dir, "config.env"), "wb") as file:
            file.write(b"NODE_ID=node\r\n")
        name, cwd = os.name, os.getcwd()
        os.name = "nt"
        os.chdir(self.target_dir)
        try:
            font_cache = self.node._build_font_cache()
        finally:
            os.name = name
            os.chdir(cwd)
        self.assertEqual(
            os.path.realpath(font_cache.path),
            os.path.realpath(os.path.join(self.target_dir, "fonts")),
        )

    def test_build_font_cache_invalid(self):
        # an index of the font cache that fails to load (eg: corrupted by a
        # power loss) doesn't prevent the node from running, that starts with
        # an empty cache where the fonts are installed again
        self.node.font_cache.install(self._font())
        with open(os.path.join(self.fonts_dir, "index.json"), "wb") as file:
            file.write(b"\x00" * 64)
        appier.conf_s("FONTS_PATH", self.fonts_dir)
        try:
            font_cache = self.node._build_font_cache()
        finally:
            appier.conf_r("FONTS_PATH")
        self.assertEqual(font_cache.path, self.fonts_dir)
        self.assertEqual(font_cache.installed(), [])
        self.assertEqual(font_cache.files(), {})
        font = font_cache.install(self._font())
        self.assertEqual(font_cache.installed()[0]["md5"], font["md5"])

    def test_install_fonts(self):
        fonts = self.node._install_fonts([self._font(), self._font(name="Binaria")])
        self.assertEqual([font["name"] for font in fonts], ["Colonia", "Binaria"])
        self.assertEqual(MockNPColonyWindows.fonts, [])

        # installs the fonts on windows, where all the installed fonts
        # are loaded in the system (GDI) for the printing
        sys.modules["npcolony"] = MockNPColonyWindows
        fonts = self.node._install_fonts([self._font()])
        self.assertEqual(fonts[0]["path"] in self.node.loaded_fonts, True)
        self.assertEqual(
            MockNPColonyWindows.fonts,
            [("load", path) for path in sorted(self.node.font_cache.files().values())],
        )

        # one of the fonts fails to install after the previous one has been
        # installed (as the active one), that is still loaded in the system
        MockNPColonyWindows.fonts = []
        data = build_font("Fontana")
        font = dict(name="Fontana", data_b64=base64.b64encode(data).decode())
        self.assertRaises(
            appier.OperationalError,
            lambda: self.node._install_fonts(
                [font, dict(name="Binaria", md5="0" * 32)]
            ),
        )
        path = self.node.font_cache._file(hashlib.md5(data).hexdigest())
        self.assertEqual(MockNPColonyWindows.fonts, [("load", path)])
        self.assertEqual(path in self.node.loaded_fonts, True)

        # a font of the job that fails to load in the system fails the job,
        # while a (broken) font of the cache that is not of the job doesn't
        data = build_font("Telhado")
        font = dict(name="Telhado", data_b64=base64.b64encode(data).decode())
        path = self.node.font_cache._file(hashlib.md5(data).hexdigest())
        MockNPColonyWindows.errors = {path: IOError("Problem loading font")}
        self.assertRaises(
            appier.OperationalError, lambda: self.node._install_fonts([font])
        )
        fonts = self.node._install_fonts([self._font(name="Fontana")])
        self.assertEqual(fonts[0]["name"], "Fontana")
        self.assertEqual(path in self.node.loaded_fonts, False)

        # two files of the same font in the job, the last one is the active
        # one (loaded) and the first one is not required to be loaded
        data = build_font("Ovelhas")
        fonts = self.node._install_fonts(
            [
                dict(name="Ovelhas", data_b64=base64.b64encode(data).decode()),
                dict(name="Ovelhas", data_b64=base64.b64encode(data + b"\0").decode()),
            ]
        )
        self.assertEqual(fonts[0]["path"] in self.node.loaded_fonts, False)
        self.assertEqual(fonts[1]["path"] in self.node.loaded_fonts, True)

    def test_load_fonts(self):
        regular = self.node.font_cache.install(self._font())
        binaria = self.node.font_cache.install(self._font(name="Binaria"))

        # the npcolony of the system (CUPS) doesn't load fonts
        self.node._load_fonts()
        self.assertEqual(self.node.loaded_fonts, set())

        sys.modules["npcolony"] = MockNPColonyWindows
        self.node._load_fonts()
        self.assertEqual(
            MockNPColonyWindows.fonts,
            [("load", path) for path in sorted([regular["path"], binaria["path"]])],
        )
        self.assertEqual(
            self.node.loaded_fonts, set([regular["path"], binaria["path"]])
        )

        # installs an updated file of the font, that replaces the loaded one
        # (unloaded) as the active one for its family and style
        MockNPColonyWindows.fonts = []
        data = build_font() + b"\0"
        updated = self.node.font_cache.install(
            dict(name="Colonia", data_b64=base64.b64encode(data))
        )
        self.node._load_fonts()
        self.assertEqual(
            MockNPColonyWindows.fonts,
            [("unload", regular["path"]), ("load", updated["path"])],
        )
        self.assertEqual(
            self.node.loaded_fonts, set([updated["path"], binaria["path"]])
        )

        MockNPColonyWindows.fonts = []
        self.node._load_fonts()
        self.assertEqual(MockNPColonyWindows.fonts, [])

        # a font that fails to load (eg: refused by GDI) doesn't prevent the
        # other fonts from loading, and it's retried on the next load
        MockNPColonyWindows.fonts = []
        self.node.loaded_fonts = set()
        MockNPColonyWindows.errors = {updated["path"]: IOError("Problem loading")}
        self.node._load_fonts()
        self.assertEqual(MockNPColonyWindows.fonts, [("load", binaria["path"])])
        self.assertEqual(self.node.loaded_fonts, set([binaria["path"]]))
        MockNPColonyWindows.errors = dict()
        self.node._load_fonts()
        self.assertEqual(
            self.node.loaded_fonts, set([updated["path"], binaria["path"]])
        )

        # a font that fails to unload is no longer considered loaded, as it's
        # not used anymore (another file of the font is active)
        MockNPColonyWindows.fonts = []
        MockNPColonyWindows.errors = {updated["path"]: IOError("Problem unloading")}
        self.node.font_cache.install(dict(name="Colonia", md5=regular["md5"]))
        self.node._load_fonts()
        self.assertEqual(MockNPColonyWindows.fonts, [("load", regular["path"])])
        self.assertEqual(
            self.node.loaded_fonts, set([regular["path"], binaria["path"]])
        )
        MockNPColonyWindows.errors = dict()
        MockNPColonyWindows.fonts = []

        # the npcolony of the system doesn't report the loading of fonts
        # (eg: a build without the feature), so the fonts are not loaded
        MockNPColonyWindows.features = []
        self.node.loaded_fonts = set()
        self.node._load_fonts()
        self.assertEqual(MockNPColonyWindows.fonts, [])
        self.assertEqual(self.node.loaded_fonts, set())

        sys.modules["npcolony"] = None
        self.node._load_fonts()
        self.assertEqual(MockNPColonyWindows.fonts, [])

    def test_restart_exit(self):
        # the node restarts by exiting with the (error) exit code reserved
        # for it, so that its service starts it again
        colony_print.node.sys = MockSys
        colony_print.node.os = MockOS
        colony_print.node.subprocess = MockSubprocess
        self.node.node_restart = "exit"
        self.assertRaises(MockInterrupt, self.node._restart)
        self.assertEqual(MockSys.exits, [colony_print.node.RESTART_CODE])
        self.assertEqual(colony_print.node.RESTART_CODE > 0, True)
        self.assertEqual(MockOS.execs, [])
        self.assertEqual(MockSubprocess.calls, [])

        # the same happens on windows, where the service is the one that
        # starts the node again
        MockOS.name = "nt"
        self.assertRaises(MockInterrupt, self.node._restart)
        self.assertEqual(MockSys.exits, [colony_print.node.RESTART_CODE] * 2)
        self.assertEqual(MockSubprocess.calls, [])

    def test_restart_exec(self):
        # the node restarts by replacing its process with the original
        # command line of the interpreter (with its options) and with the
        # environment the process was started with (without the values of
        # the boot), so that a changed configuration applies
        colony_print.node.sys = MockSys
        colony_print.node.os = MockOS
        colony_print.node.subprocess = MockSubprocess
        MockOS.environ = dict(PATH="/usr/bin", SECRET_KEY="key", NODE_BOOT="1")
        appier.conf_s("NODE_BOOT_KEYS", "NODE_BOOT,NODE_BOOT_KEYS,SECRET_KEY")
        self.node.node_restart = "exec"
        try:
            self.assertRaises(MockInterrupt, self.node._restart)
        finally:
            appier.conf_r("NODE_BOOT_KEYS")
        self.assertEqual(
            MockOS.execs,
            [
                (
                    "/usr/bin/python",
                    [
                        "/usr/bin/python",
                        "-I",
                        "-u",
                        "boot.py",
                        "--config",
                        "config.env",
                    ],
                    dict(PATH="/usr/bin"),
                )
            ],
        )
        self.assertEqual(MockSys.exits, [])
        self.assertEqual(MockSubprocess.calls, [])

        # the interpreters that don't keep their original command line run
        # the one of their script (without the options of the interpreter)
        colony_print.node.sys = MockSysLegacy
        MockOS.execs = []
        self.assertRaises(MockInterrupt, self.node._restart)
        self.assertEqual(
            MockOS.execs[0][:2],
            (
                "/usr/bin/python",
                ["/usr/bin/python", "boot.py", "--config", "config.env"],
            ),
        )
        self.assertEqual(MockSysLegacy.argv, ["boot.py", "--config", "config.env"])

        # a process that can't be replaced fails the restart
        MockOS.error = OSError("Exec format error")
        self.assertRaises(OSError, self.node._restart)
        self.assertEqual(MockSys.exits, [])

    def test_restart_exec_windows(self):
        # a process can't be replaced on windows, so a new one is started
        # (with the same command line and environment) and the current one
        # exits (with success), only once the new one is started
        colony_print.node.sys = MockSys
        colony_print.node.os = MockOS
        colony_print.node.subprocess = MockSubprocess
        MockOS.name = "nt"
        MockOS.environ = dict(PATH="C:\\Windows", SECRET_KEY="key")
        MockSys.executable = "C:\\Python\\python.exe"
        self.node.node_restart = "exec"
        try:
            self.assertRaises(MockInterrupt, self.node._restart)
            self.assertEqual(
                MockSubprocess.calls,
                [
                    (
                        [
                            "C:\\Python\\python.exe",
                            "-I",
                            "-u",
                            "boot.py",
                            "--config",
                            "config.env",
                        ],
                        dict(PATH="C:\\Windows", SECRET_KEY="key"),
                    )
                ],
            )
            self.assertEqual(MockSys.exits, [0])
            self.assertEqual(MockOS.execs, [])

            # the node keeps running when the new process can't be started
            MockSubprocess.error = OSError("The system cannot find the file")
            self.assertRaises(OSError, self.node._restart)
            self.assertEqual(MockSys.exits, [0])
        finally:
            MockSys.executable = "/usr/bin/python"

    def test_restart_invalid(self):
        colony_print.node.sys = MockSys
        colony_print.node.os = MockOS
        colony_print.node.subprocess = MockSubprocess
        for restart in (None, "0", "reboot"):
            self.node.node_restart = restart
            self.assertRaises(appier.OperationalError, self.node._restart)
        self.assertEqual(MockSys.exits, [])
        self.assertEqual(MockOS.execs, [])
        self.assertEqual(MockSubprocess.calls, [])

    def test_environ(self):
        # the node that is not run by the boot restarts with its environment
        colony_print.node.os = MockOS
        MockOS.environ = dict(
            PATH="/usr/bin",
            BASE_URL="https://print.example.com/",
            SECRET_KEY="key",
            NODE_BOOT="1",
            NODE_BOOT_KEYS="NODE_BOOT,NODE_BOOT_KEYS,NODE_UPDATE_ERROR,SECRET_KEY",
        )
        self.assertEqual(self.node._environ(), MockOS.environ)
        self.assertEqual(self.node._environ() is MockOS.environ, False)

        # the values set by the boot (as named by it) are not part of the
        # environment of the restarted node, the ones that are not in the
        # environment (eg: removed meanwhile) being ignored
        appier.conf_s("NODE_BOOT_KEYS", MockOS.environ["NODE_BOOT_KEYS"])
        try:
            self.assertEqual(
                self.node._environ(),
                dict(PATH="/usr/bin", BASE_URL="https://print.example.com/"),
            )
        finally:
            appier.conf_r("NODE_BOOT_KEYS")
        self.assertEqual(len(MockOS.environ), 5)

    def test_save_state(self):
        # the state file is created with the values, that are loaded back
        # by the boot, leaving no temporary file behind
        import colony_print.boot

        boot = colony_print.boot.ColonyPrintBoot(environ=dict())
        self.node.node_state = self.state_path
        self.node._save_state(NODE_UPDATE_ONCE="1")
        self.assertEqual(self._state(), b"NODE_UPDATE_ONCE=1\r\n")
        self.assertEqual(boot.load_config(self.state_path), dict(NODE_UPDATE_ONCE="1"))

        # the values are replaced, the other ones being kept
        self.node._save_state(NODE_UPDATE="0")
        self.node._save_state(NODE_UPDATE="1")
        self.assertEqual(
            boot.load_config(self.state_path),
            dict(NODE_UPDATE="1", NODE_UPDATE_ONCE="1"),
        )
        self.assertEqual(sorted(os.listdir(self.target_dir)), ["state.env"])

        # the state saved by the node is the one applied by the boot
        self.assertEqual(boot.apply_state(self.state_path), True)
        self.assertEqual(boot.environ, dict(NODE_UPDATE="1"))
        self.assertEqual(self._state(), b"NODE_UPDATE=1\r\n")

        # the node that is not run by the boot has no state file
        self.node.node_state = None
        self.assertRaises(Exception, lambda: self.node._save_state(NODE_UPDATE="0"))

    def test_has_feature(self):
        self.assertEqual(self.node._has_feature("load-fonts"), False)

        sys.modules["npcolony"] = MockNPColonyWindows
        self.assertEqual(self.node._has_feature("load-fonts"), True)
        self.assertEqual(self.node._has_feature("unknown"), False)

        MockNPColonyWindows.features = []
        self.assertEqual(self.node._has_feature("load-fonts"), False)

        sys.modules["npcolony"] = MockNPColonyLegacy
        self.assertEqual(self.node._has_feature("load-fonts"), False)

    def test_is_enabled(self):
        self.assertEqual(self.node._is_enabled("NODE_CONTROL"), True)
        self.assertEqual(self.node._is_enabled("NODE_BOOT", default="0"), False)

        try:
            for value in ("0", "false", "False", "no", " off ", 0, False):
                appier.conf_s("NODE_CONTROL", value)
                self.assertEqual(self.node._is_enabled("NODE_CONTROL"), False)

            for value in ("1", "true", "yes", "", 1, True):
                appier.conf_s("NODE_CONTROL", value)
                self.assertEqual(self.node._is_enabled("NODE_CONTROL"), True)
                self.assertEqual(
                    self.node._is_enabled("NODE_CONTROL", default="0"), True
                )
        finally:
            appier.conf_r("NODE_CONTROL")

    def test_info_distribution(self):
        self.assertEqual(self.node._info_distribution(), None)

        self._os_release(
            b"# the description of the operating system\n"
            + b'NAME="Debian GNU/Linux"\n'
            + b'PRETTY_NAME="Debian GNU/Linux 12 (bookworm)"\n'
            + b'VERSION_ID="12"\n'
        )
        self.assertEqual(
            self.node._info_distribution(), "Debian GNU/Linux 12 (bookworm)"
        )

        self._os_release(b"NAME='Alpine Linux'\r\nPRETTY_NAME='Alpine Linux v3.20'\r\n")
        self.assertEqual(self.node._info_distribution(), "Alpine Linux v3.20")

        self._os_release(b"PRETTY_NAME=Arch Linux\n")
        self.assertEqual(self.node._info_distribution(), "Arch Linux")

        self._os_release(b'PRETTY_NAME="Linux a=b"\n')
        self.assertEqual(self.node._info_distribution(), "Linux a=b")

    def test_info_distribution_invalid(self):
        self._os_release(b'NAME="Ubuntu"\nVERSION_ID="24.04"\n')
        self.assertEqual(self.node._info_distribution(), None)

        self._os_release(b'# PRETTY_NAME="Ubuntu 24.04.1 LTS"\n')
        self.assertEqual(self.node._info_distribution(), None)

        self._os_release(b'PRETTY_NAME=""\n')
        self.assertEqual(self.node._info_distribution(), None)

        self._os_release(b"")
        self.assertEqual(self.node._info_distribution(), None)

        self._os_release(b'PRETTY_NAME="Ubuntu \xff\xfe"\n')
        self.assertEqual(self.node._info_distribution(), None)

        colony_print.node.OS_RELEASE_PATHS = (self.target_dir,)
        self.assertEqual(self.node._info_distribution(), None)

        colony_print.node.OS_RELEASE_PATHS = ()
        self.assertEqual(self.node._info_distribution(), None)

    def test_info_distribution_paths(self):
        fallback_path = os.path.join(self.target_dir, "os-release-fallback")
        colony_print.node.OS_RELEASE_PATHS = (self.os_release_path, fallback_path)
        self._os_release(b'PRETTY_NAME="Fedora Linux 40"\n', path=fallback_path)
        self.assertEqual(self.node._info_distribution(), "Fedora Linux 40")

        self._os_release(b'PRETTY_NAME="Ubuntu 24.04.1 LTS"\n')
        self.assertEqual(self.node._info_distribution(), "Ubuntu 24.04.1 LTS")

        # the fallback is only used when the first file is missing, so
        # its description is never used for a first file without one
        self._os_release(b'NAME="Ubuntu"\nVERSION_ID="24.04"\n')
        self.assertEqual(self.node._info_distribution(), None)

        self._os_release(b'PRETTY_NAME=""\n')
        self.assertEqual(self.node._info_distribution(), None)

        self._os_release(b'PRETTY_NAME="Ubuntu \xff\xfe"\n')
        self.assertEqual(self.node._info_distribution(), None)

        os.remove(self.os_release_path)
        self.assertEqual(self.node._info_distribution(), "Fedora Linux 40")

        os.mkdir(self.os_release_path)
        self.assertEqual(self.node._info_distribution(), "Fedora Linux 40")

    def test_ensure_format(self):
        self.node._ensure_format(None)
        self.node._ensure_format("pdf")
        self.node._ensure_format("binie")
        self.node._ensure_format("xmpl")
        self.assertRaises(
            appier.OperationalError, lambda: self.node._ensure_format("zpl")
        )

        MockNPColony.format = "binie"
        self.node._ensure_format("binie")
        self.node._ensure_format("xmpl")
        self.assertRaises(
            appier.OperationalError, lambda: self.node._ensure_format("pdf")
        )

        sys.modules["npcolony"] = MockNPColonyLegacy
        self.node._ensure_format("pdf")

    def test_ensure_capability(self):
        self.node._ensure_capability("xmpl")
        self.node._ensure_capability("dynamic-fonts")
        self.assertRaises(
            appier.OperationalError, lambda: self.node._ensure_capability("email")
        )
        self.assertRaises(
            appier.OperationalError, lambda: self.node._ensure_capability("unknown")
        )

        sys.modules["npcolony"] = MockNPColonyLegacy
        self.node._ensure_capability("xmpl")
        self.assertRaises(
            appier.OperationalError,
            lambda: self.node._ensure_capability("dynamic-fonts"),
        )
