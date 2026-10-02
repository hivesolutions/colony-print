#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import time
import uuid
import json
import base64
import shutil
import struct
import logging
import tempfile
import platform
import traceback
import subprocess

import appier

NAME = "colony-print"
""" The name of the program currently running """

VERSION = "0.23.0"
""" The version of the colony print node currently running,
this value should be updated whenever a new version is released """

BASE_URL = "https://print.bemisc.com/"
""" The default base URL to be used for the communication with the
Colony Print server """

SLEEP_TIME = 3.0
""" The default time to sleep between each iteration, this value
is used to avoid overloading the server with requests """

NODE_MODES = set(["normal", "email"])
""" The set of running modes that are considered to be valid for
the node, this is going to be used to validate the mode """

RESTART_MODES = set(["exit", "exec"])
""" The set of ways in which the node is able to restart itself (as
requested from the admin), either by exiting, so that its service
starts it again, or by running its own command line once more """

RESTART_CODE = 75
""" The exit code (reserved for it) of the process of a node that
restarts by exiting, which is an error one, as the services only
start again (by themselves) the processes that exit with an error """

COMMAND_TYPES = ("restart", "update", "auto-update")
""" The types of the jobs that are commands for the node (requested
from the admin), instead of documents to be printed, so they have no
data and are handled in the same way by every mode of the node """

FALSE_VALUES = ("0", "false", "no", "off")
""" The (lower cased) configuration values considered to be false,
the same ones as the ones of the boot of the node """

FONTS_PATH = "~/.colony_print/fonts"
""" The default path to the directory of the cache of the fonts
installed on demand, the ones sent with the print jobs """

SIZE_TOLERANCE = 72.0 / 25.4
""" The tolerance (in points, one millimeter) of the comparison of
the size of a document with the size of the media of a printer and
with the limits of its custom sizes, as the sizes of the printers
are rounded (eg: to points) """

LIBRARIES = (
    ("npcolony", "npcolony", "VERSION"),
    ("gravo_pilot", "gravo_pilot", "VERSION"),
    ("appier", "appier", "VERSION"),
    ("appier-extras", "appier_extras", "VERSION"),
    ("pillow", "PIL", "__version__"),
    ("reportlab", "reportlab", "Version"),
)
""" The libraries whose versions are reported by the node, as a
sequence of tuples with the name of the library, the name of the
module to be imported and the name of its version attribute """

OS_RELEASE_PATHS = ("/etc/os-release", "/usr/lib/os-release")
""" The paths to the files that describe the distribution of the
operating system (linux only), only the first one that exists is
used, the other ones being fallbacks for when it's missing """

EMAIL_TEMPLATE = appier.legacy.u("""
Hey there!

Great news — your document **%s** has just gone through a virtual transformation and is now rocking the PDF stage! 🎸📄 Ready to take a look? Check out the attachment—it's dressed to impress.

We hope you find everything in perfect harmony. Should you need a replay, just hit 'print' again!

Keep on printing,

Your's dear 'Colony Print'

P.S. No trees were harmed in the making of this PDF. 🌳✌️
""")


class ColonyPrintNode(object):
    def __init__(self, sleep_time=SLEEP_TIME):
        self.sleep_time = sleep_time
        self.node_mode = None
        self.node_printer = None
        self.node_email_receivers = None
        self.node_restart = None
        self.node_control = True
        self.node_boot = False
        self.node_update = True
        self.node_state = None
        self.font_cache = None
        self.loaded_fonts = set()
        self.restart_jobs = []
        self.start_time = time.time()

    def loop(self):
        logging.basicConfig(
            format="%(asctime)s [%(levelname)s] %(message)s", level=logging.DEBUG
        )

        base_url = appier.conf("BASE_URL", BASE_URL)
        secret_key = appier.conf("SECRET_KEY", None)
        node_id = appier.conf("NODE_ID", "node")
        node_name = appier.conf("NODE_NAME", "node")
        node_location = appier.conf("NODE_LOCATION", "undefined")
        self.node_mode = appier.conf("NODE_MODE", "normal")
        self.node_printer = appier.conf("NODE_PRINTER", "default")
        self.node_email_receivers = appier.conf("NODE_EMAIL_RECEIVER", [], cast=list)
        self.node_email_receivers = appier.conf(
            "NODE_EMAIL_RECEIVERS", self.node_email_receivers, cast=list
        )

        # the node restarts itself (as requested from the admin) by exiting
        # when it's run by the windows service (WinSW), that starts it again,
        # and by running its own command line once more otherwise, unless the
        # way to restart is configured, any other value refusing the restart
        node_restart = appier.conf("NODE_RESTART", None)
        if node_restart in (None, ""):
            node_restart = "exit" if appier.conf("WINSW_SERVICE_ID", None) else "exec"
        node_restart = str(node_restart).strip().lower()
        self.node_restart = node_restart if node_restart in RESTART_MODES else None

        # the node is updated from the admin only when it's run by the boot,
        # that hands its marker, the path of the state file and the outcome
        # of its update over to the node, the remote control of the node
        # (restart and update) may be disabled altogether in its configuration
        self.node_control = self._is_enabled("NODE_CONTROL")
        self.node_boot = self._is_enabled("NODE_BOOT", default="0")
        self.node_update = self._is_enabled("NODE_UPDATE")
        self.node_state = appier.conf("NODE_STATE_PATH", None)

        logging.info("Booting %s %s (%s)" % (NAME, VERSION, appier.PLATFORM))
        logging.info("Running node '%s' in '%s' mode" % (node_id, self.node_mode))

        # builds the font cache of the node and loads its fonts in the
        # system, a font that fails to load is logged and doesn't prevent
        # the node from running (only the jobs that require it fail)
        self.font_cache = self._build_font_cache()
        self._load_fonts()

        headers = dict()
        if secret_key:
            headers["X-Secret-Key"] = secret_key

        while True:
            try:
                # restarts the node in case one of the jobs of the previous
                # iteration has requested it, only now that the remaining jobs
                # of its batch are printed and their results posted, so that
                # no print is interrupted, a restart that fails being posted
                # as the (error) result of the jobs that requested it
                for job_id, result in self.restart().items():
                    logging.info("Posting job result for '%s'" % job_id)
                    appier.post(
                        base_url + "nodes/%s/jobs/%s/result" % (node_id, job_id),
                        data_j=result,
                        headers=headers,
                    )

                logging.info("Submitting node information")
                appier.post(
                    base_url + "nodes/%s" % node_id,
                    data_j=dict(
                        name=node_name,
                        location=node_location,
                        mode=self.node_mode,
                        printer=self.node_printer,
                        engines=self.engines,
                        engine_info=self.engine_info,
                        libraries=self.libraries,
                        capabilities=self.capabilities,
                        fonts=self.font_cache.installed(),
                        platform=appier.PLATFORM,
                        os=os.name,
                        system=self.system,
                        version=VERSION,
                        start_time=self.start_time,
                        update=self.update,
                    ),
                    headers=headers,
                )
                logging.info("Retrieving jobs for node '%s'" % node_id)
                jobs = appier.get(
                    base_url + "nodes/%s/jobs" % node_id, headers=headers, timeout=600
                )
                logging.info("Retrieved %d jobs for node '%s'" % (len(jobs), node_id))
                results = dict()
                for job in jobs:
                    try:
                        result = self.print_job(job)
                    except Exception as exception:
                        logging.exception(
                            "Exception while printing job '%s': %s"
                            % (job["id"], str(exception))
                        )
                        result = dict(
                            result="error",
                            error=str(exception),
                            traceback=traceback.format_exc(),
                        )

                    # the jobs that restart the node have no result, as they
                    # are finished by the server once the node (restarted)
                    # registers itself again
                    if result == None:
                        continue
                    results[job["id"]] = result
                for job_id, result in results.items():
                    logging.info("Posting job result for '%s'" % job_id)
                    appier.post(
                        base_url + "nodes/%s/jobs/%s/result" % (node_id, job_id),
                        data_j=result,
                        headers=headers,
                    )
            except Exception as exception:
                logging.exception("Exception while looping '%s'" % str(exception))
                logging.info("Sleeping for %.2f seconds" % self.sleep_time)
                time.sleep(self.sleep_time)

    def print_job(self, job):
        if not self.node_mode in NODE_MODES:
            raise appier.OperationalError("Mode '%s' not valid" % self.node_mode)
        return getattr(self, "print_job_" + self.node_mode)(job)

    def print_job_normal(self, job):
        return self._handle_job(job)

    def print_job_email(self, job):
        # the jobs that don't print a document (eg: the installation of
        # fonts and the commands) are handled as in the normal mode, as
        # there's no output document to be generated and sent by email
        if job.get("type", None) in ("fonts",) + COMMAND_TYPES:
            return self._handle_job(job)

        import mailme

        data_b64 = job["data_b64"]
        name = job.get("name", "undefined")
        printer = job.get("printer", None)
        format = job.get("format", None)
        options = job.get("options", dict())
        fonts = job.get("fonts", None)
        save_output = options.get("save_output", False)
        send_email = options.get("send_email", True)
        safe_sleep = options.get("safe_sleep", 0.0)
        printer_s = appier.legacy.u(printer if printer else self.node_printer)
        short_name = name[-12:]

        self._ensure_format(format)

        temp_dir = tempfile.mkdtemp()
        try:
            logging.debug(
                "Created temporary directory '%s' for document generation" % temp_dir
            )

            output_path = os.path.join(temp_dir, "%s.pdf" % str(uuid.uuid4()))
            options["output_path"] = output_path
            logging.info(
                "Generating document job '%s' with '%s' printer" % (name, printer_s)
            )

            # sends the print job for handling using npcolony, this will make
            # sure that the job is printed in the current system
            self._handle_npcolony(
                data_b64, format=format, printer=printer_s, options=options, fonts=fonts
            )

            # does some busy waiting for the output file to be created
            # note that the process of handling the PDF printing is
            # asynchronous and may take some time to be completed
            for _ in range(10):
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    time.sleep(safe_sleep)
                    break
                time.sleep(0.5)

            file = open(output_path, "rb")
            try:
                output_data = file.read()
            finally:
                file.close()

            # encodes the output data as base64 so that it may be sent
            # as part of the email message, this is required for the
            # attachment of the PDF file to the email message
            output_data_b64 = base64.b64encode(output_data)

            # computes the complete list of email receivers using the
            # base instance value and the ones provided via options,
            # makes sure that the email receivers are unique
            email_receivers = options.get("email_receivers", [])
            email_receiver = options.get("email_address", None)
            email_receiver = options.get("email_receiver", email_receiver)
            email_override = options.get("email_override", True)
            if email_receiver:
                email_receivers.append(email_receiver)
            email_receivers = (
                email_receivers
                if email_override and email_receivers
                else list(self.node_email_receivers) + email_receivers
            )

            if send_email:
                logging.info(
                    "Sending email to %s for job '%s' with '%s' printer"
                    % (",".join(email_receivers), name, printer_s)
                )

                # creates the mailme API instance and sends the email with
                # the generated PDF file as attachment to the email receivers
                api = mailme.API()
                api.send(
                    mailme.MessagePayload(
                        receivers=email_receivers,
                        title="Your PDF Masterpiece Awaits!",
                        subject="Print Job %s is Ready!" % short_name,
                        contents=appier.legacy.bytes(
                            EMAIL_TEMPLATE % name, encoding="utf-8", force=True
                        ),
                        attachments=[
                            mailme.AttachmentPayload(
                                name="%s.pdf" % name,
                                data=output_data_b64.decode(),
                                mime="application/pdf",
                            )
                        ],
                    )
                )
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

        return dict(
            result="success",
            mode="email",
            handler="npcolony",
            email_sent=send_email,
            output_saved=save_output,
            receivers=email_receivers if send_email else None,
            output_data=output_data_b64.decode() if save_output else None,
            output_encoding="base64" if save_output else None,
            output_mime_type="application/pdf" if save_output else None,
        )

    def restart(self):
        """
        Restarts the node in case its restart was requested by one of its
        jobs (restart or update), which only returns in case the restart
        fails, with the (error) results of those jobs, as the server only
        finishes them (by itself) once the restarted node registers itself.

        :rtype: Dictionary
        :return: The results of the jobs that requested the restart (by
        job identifier), empty in case no restart was requested.
        """

        results = dict()
        job_ids, self.restart_jobs = self.restart_jobs, []
        if not job_ids:
            return results

        try:
            self._restart()
        except Exception as exception:
            logging.exception("Exception while restarting node: %s" % str(exception))
            for job_id in job_ids:
                results[job_id] = dict(
                    result="error",
                    error=str(exception),
                    traceback=traceback.format_exc(),
                )
        return results

    @property
    def npcolony(self):
        import npcolony

        return npcolony

    @property
    def engines(self):
        engines = []
        if self._has_npcolony():
            engines.append("npcolony")
        if self._has_gravo():
            engines.append("gravo")
        if self._has_text():
            engines.append("text")
        return engines

    @property
    def engine_info(self):
        engine_info = dict()
        if self._has_npcolony() and hasattr(self, "_info_npcolony"):
            engine_info["colony"] = self._info_npcolony()
        if self._has_gravo() and hasattr(self, "_info_gravo"):
            engine_info["gravo"] = self._info_gravo()
        if self._has_text() and hasattr(self, "_info_text"):
            engine_info["text"] = self._info_text()
        return engine_info

    @property
    def libraries(self):
        # builds the map of the versions of the libraries of the node, the
        # libraries that are not installed (or that don't expose a version)
        # are omitted, as their version is not known
        libraries = dict()
        for name, module, attribute in LIBRARIES:
            try:
                module = __import__(module)
            except Exception:
                continue
            if not hasattr(module, attribute):
                continue
            libraries[name] = getattr(module, attribute)
        return libraries

    @property
    def system(self):
        # builds the map with the information of the operating system of
        # the node, the distribution is only set for the systems that
        # describe it (linux), note that the architecture (32bit or 64bit)
        # is the one of the interpreter running the node, which may be
        # different from the one of the machine
        system = dict(
            name=platform.system(),
            release=platform.release(),
            version=platform.version(),
            machine=platform.machine(),
            architecture="%dbit" % (struct.calcsize("P") * 8),
        )
        distribution = self._info_distribution()
        if distribution:
            system["distribution"] = distribution
        return system

    @property
    def update(self):
        """
        The information of the update of the packages of the node, if it's
        run every time the node starts (auto-update) and the outcome of the
        one run by the boot when the node started (its status, its time and
        its error), which is only known by the nodes run by the boot.

        :rtype: Dictionary
        :return: The information of the update of the node, or an invalid
        value in case the node is not run by the boot.
        """

        if not self.node_boot:
            return None
        update = dict(
            auto=self.node_update,
            status=appier.conf("NODE_UPDATE_STATUS", None),
            time=appier.conf("NODE_UPDATE_TIME", None, cast=float),
        )
        error = appier.conf("NODE_UPDATE_ERROR", None)
        if error:
            update["error"] = error
        return update

    @property
    def capabilities(self):
        """
        The capabilities (features) supported by the node, as advertised
        to the server, that depend on the available engines, on the system
        (and its npcolony version), on the mode of the node and on the way
        the node is run (and configured) for the ones of its remote control.

        :rtype: List
        :return: The names of the capabilities supported by the node.
        :see: https://github.com/hivesolutions/colony-print/blob/master/doc/capabilities.md
        """

        capabilities = list(self.engines)
        if self._has_npcolony():
            format = (
                self.npcolony.get_format()
                if hasattr(self.npcolony, "get_format")
                else "binie"
            )
            capabilities.extend(["binie", "xmpl"])
            if format == "pdf":
                capabilities.append("pdf")
            if format == "binie" or [
                device for device in self.npcolony.get_devices() if "custom" in device
            ]:
                capabilities.append("custom-paper")
            if format == "pdf" or self._has_feature("load-fonts"):
                capabilities.append("dynamic-fonts")
        if self._has_gravo():
            capabilities.extend(
                ["gravo-extra-fonts", "gravo-record", "gravo-check-path"]
            )
        if self.node_mode == "email":
            capabilities.append("email")
        if self.node_control:
            if self.node_restart:
                capabilities.append("restart")
            if self.node_restart and self.node_boot:
                capabilities.append("update")
            if self.node_boot:
                capabilities.append("auto-update")
        return capabilities

    def _handle_job(self, job):
        # unpacks the complete set of job information to
        # be able to print the job in the current system,
        # the jobs that are commands having no data
        data_b64 = job.get("data_b64", None)
        name = job.get("name", "undefined")
        printer = job.get("printer", None)
        type = job.get("type", None)
        format = job.get("format", None)
        options = job.get("options", dict())
        fonts = job.get("fonts", None)

        # handles the name of the printer as an unicode string, as the one of
        # the node is a byte string (encoded as UTF-8) in Python 2, that can't
        # be mixed with the unicode strings of the job when it's not ASCII
        printer_s = appier.legacy.u(printer if printer else self.node_printer)

        logging.info("Printing job '%s' with '%s' printer" % (name, printer_s))
        if format:
            logging.info("Using format '%s' for job '%s'" % (format, name))

        if type in (None, "npcolony"):
            options["title"] = name
            result = self._handle_npcolony(
                data_b64, format=format, printer=printer_s, options=options, fonts=fonts
            )
            return dict(
                result="success", handler="npcolony", printer=printer_s, data=result
            )
        elif type in ("gravo",):
            result = self._handle_gravo(data_b64)
            return dict(result="success", handler="gravo", data=result)
        elif type in ("text",):
            result = self._handle_text(data_b64)
            return dict(result="success", handler="text", data=result)
        elif type in ("fonts",):
            result = self._handle_fonts(data_b64)
            return dict(result="success", handler="fonts", data=result)
        elif type in ("restart", "update"):
            self._handle_restart(job["id"], update=type == "update")
            return None
        elif type in ("auto-update",):
            result = self._handle_auto_update(options)
            return dict(result="success", handler="auto-update", data=result)

        raise appier.OperationalError("Type '%s' not valid" % type)

    def _handle_npcolony(
        self, data_b64, format=None, printer=None, options=dict(), fonts=None
    ):
        if not self._has_npcolony():
            raise appier.OperationalError("npcolony engine is not available")

        # in case the data is an XMPL document converts it into a binie
        # document (printed by every system), together with the fonts
        # declared by the document, that are added to the job ones
        if format == "xmpl":
            self._ensure_capability("xmpl")
            data_b64, fonts = self._convert_xmpl(data_b64, fonts=fonts)
            format = "binie"

        # installs the fonts of the job (if any) so that they're used in
        # the printing of the document, as the fonts of the system are
        if fonts:
            self._ensure_capability("dynamic-fonts")
            self._install_fonts(fonts)

        # in case the data is a binie document and the current system only
        # prints pdf documents (eg: cups) converts the document into a pdf
        # one laid out for the printer, resulting in the same windows layout
        if self._is_binie(data_b64, format=format):
            data_b64, options = self._convert_binie(
                data_b64, printer=printer, options=options
            )
            format = "pdf"

        self._ensure_format(format)

        # encodes the name of the printer (as UTF-8) in Python 2, as npcolony
        # only accepts it as an unicode string when it's ASCII (unlike the
        # values of the options, that are encoded by npcolony), the encoded
        # name being converted by npcolony into the one of the system (eg:
        # the ANSI code page of windows)
        if printer and not isinstance(printer, str):
            printer = printer.encode("utf-8")

        if printer:
            self.npcolony.print_printer_base64(printer, data_b64, options=options)
        else:
            self.npcolony.print_base64(data_b64)

        return dict()

    def _is_binie(self, data_b64, format=None):
        """
        Verifies if the provided (base64 encoded) data is a binie
        document that must be converted into a PDF document, which
        is the case for systems that only print PDF documents (CUPS).

        Data without format is only considered a binie document in
        case its structure is valid, so that any other data (eg: a PDF
        document) keeps being sent untouched to the printer.

        :type data_b64: String
        :param data_b64: The base64 encoded data of the job.
        :type format: String
        :param format: The format of the data of the job, if any.
        :rtype: bool
        :return: If the data is a binie document to be converted.
        """

        import colony_print

        if not hasattr(self.npcolony, "get_format"):
            return False
        if not self.npcolony.get_format() == "pdf":
            return False
        if format:
            return format == "binie"

        try:
            data = base64.b64decode(data_b64)
        except Exception:
            return False
        return colony_print.valid_binie(data)

    def _convert_binie(self, data_b64, printer=None, options=dict()):
        """
        Converts the provided (base64 encoded) binie document into a PDF
        document laid out for the media and the printable area of the
        target printer, returning it together with the print options.

        The size of the document, when it's defined, is requested as a
        custom paper size (as windows does) and used for its pages when
        the printer accepts it, otherwise the document is laid out in the
        media of the printer, from the top left corner of its printable
        area, as the windows driver of the printer does. The resulting
        media is explicitly requested and no scaling is applied, as the
        document is already laid out for the printer.

        :type data_b64: String
        :param data_b64: The base64 encoded binie document.
        :type printer: String
        :param printer: The name of the target printer, the default
        printer is used for an invalid or the default name.
        :type options: Dictionary
        :param options: The options of the job, that take precedence
        over the ones calculated for the printer, except for the media
        that is always the one the document is laid out for.
        :rtype: Tuple
        :return: The base64 encoded PDF document and the options to be
        used for its printing.
        """

        import colony_print

        # decodes the binie document that is going to be converted
        data = base64.b64decode(data_b64)

        # retrieves the target device (printer) and calculates the size of
        # its media and its margins (in points) from its imageable area
        device = self._device(printer)
        size, margins = None, None
        media = device.get("media", None)
        device_width = device.get("width", 0.0)
        device_length = device.get("length", 0.0)
        if device_width > 0 and device_length > 0:
            size = (device_width, device_length)
            margins = (
                device.get("left", 0.0),
                device.get("bottom", 0.0),
                device_width - device.get("right", device_width),
                device_length - device.get("top", device_length),
            )

        # retrieves the size defined in the header of the (valid) document
        # (tenths of millimeter), requested as a custom paper size (as windows
        # does) that is used for the pages, with the margins of the custom
        # sizes, only when the printer accepts it, otherwise the document is
        # laid out in the media of the printer, as its windows driver does,
        # note that the size is always used when the printer is unknown
        width, height = 0, 0
        if colony_print.valid_binie(data):
            width, height = struct.unpack_from("<II", data, 256)
        custom = width > 0 and height > 0
        if custom and size:
            custom = self._is_custom(
                device, (width / 254.0 * 72.0, height / 254.0 * 72.0)
            )
            if custom:
                margins = (
                    device["custom"]["margin_left"],
                    device["custom"]["margin_bottom"],
                    device["custom"]["margin_right"],
                    device["custom"]["margin_top"],
                )
        if custom:
            media = "Custom.%gx%gmm" % (width / 10.0, height / 10.0)

        # renders the binie document as a pdf document using the size and
        # the margins of the printer (or the custom size of the document)
        # and the fonts installed on demand (before the ones of the system),
        # an exception is raised in case the document is not valid
        font_files = self.font_cache.files() if self.font_cache else None
        renderer = colony_print.BinieRenderer(
            size=size, margins=margins, custom=custom, font_files=font_files
        )
        buffer = appier.legacy.BytesIO()
        renderer.render(data, buffer)
        data_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

        # builds the options of the pdf document keeping the options of the
        # job, except for the media that is always the one the document is
        # laid out for (the one of the job would not match its pages), and
        # requesting no scaling in case the job doesn't define one
        options = dict(options)
        options.pop("media", None)
        if media:
            options["media"] = media
        options.setdefault("scaling", "none")
        return data_b64, options

    def _device(self, printer):
        """
        Retrieves the information of the device (printer) with the provided
        name, the default device is used for an invalid or the default name
        (or the single device when none is the default, as npcolony does).

        :type printer: String
        :param printer: The name of the printer to retrieve the device.
        :rtype: Dictionary
        :return: The information of the device or an empty map in case
        no device is found for the printer.
        """

        devices = self.npcolony.get_devices()
        is_default = printer in (None, "", "default")
        for device in devices:
            if is_default and device.get("is_default", False):
                return device
            if not is_default and device.get("name", "").lower() == printer.lower():
                return device
        if is_default and len(devices) == 1:
            return devices[0]
        return dict()

    def _is_custom(self, device, size):
        """
        Verifies if the provided size (width and length in points) is used
        as a custom paper size by the provided device (printer), as the
        windows driver of the printer does with the custom paper size that
        is requested for a document: the size must be in the range of the
        custom sizes the device accepts (with a tolerance, as its limits are
        rounded), and a size that matches the one of the media of the device
        is not a custom size, as it's the paper the printer is loaded with.

        The devices that don't report the custom sizes they accept (eg:
        older versions of npcolony) are considered to accept none.

        :type device: Dictionary
        :param device: The information of the device (printer), with the
        custom sizes it accepts, as reported by npcolony.
        :type size: Tuple
        :param size: The size (width and length in points) to be verified.
        :rtype: bool
        :return: If the size is used as a custom paper size by the device.
        """

        width, length = size
        custom = device.get("custom", None)
        if not custom:
            return False
        if (
            abs(width - device.get("width", 0.0)) <= SIZE_TOLERANCE
            and abs(length - device.get("length", 0.0)) <= SIZE_TOLERANCE
        ):
            return False
        min_width = custom["min_width"] - SIZE_TOLERANCE
        max_width = custom["max_width"] + SIZE_TOLERANCE
        min_length = custom["min_length"] - SIZE_TOLERANCE
        max_length = custom["max_length"] + SIZE_TOLERANCE
        return min_width <= width <= max_width and min_length <= length <= max_length

    def _convert_xmpl(self, data_b64, fonts=None):
        """
        Converts the provided (base64 encoded) XMPL document into a binie
        document, the format printed by every system, returning it together
        with the fonts of the job, the ones declared by the document followed
        by the provided ones (that take precedence, as installed after).

        :type data_b64: String
        :param data_b64: The base64 encoded XMPL document.
        :type fonts: List
        :param fonts: The fonts (entries) of the job, if any.
        :rtype: Tuple
        :return: The base64 encoded binie document and the fonts (entries)
        to be installed for its printing.
        :see: https://github.com/hivesolutions/colony-print/blob/master/doc/xmpl.md
        """

        import colony_print

        # decodes the XMPL document, verifying that it may be printed (as
        # the server may not have verified it), and retrieves the fonts it
        # declares, an exception is raised in case the document is not valid
        data = base64.b64decode(data_b64)
        colony_print.verify_xmpl(data)
        fonts = colony_print.xmpl_fonts(data) + (fonts or [])

        # converts the XMPL document into a binie document using the binie
        # printing handler of the printing manager
        manager = colony_print.PrintingManager()
        manager.load()
        buffer = appier.legacy.BytesIO()
        manager.print_language(data, dict(name="binie", file=buffer))
        data_b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
        return data_b64, fonts

    def _handle_gravo(self, data_b64):
        if not self._has_gravo():
            raise appier.OperationalError("gravo engine is not available")

        import gravo_pilot

        data_j = self._decode_payload(data_b64)

        text = data_j["text"]
        font = data_j.get("font", "HELVETICA 1L")
        font_size = data_j.get("font_size", None)
        width = data_j.get("width", 80)
        height = data_j.get("height", 100)
        margins = data_j.get("margins", None)
        dry_run = data_j.get("dry_run", False)
        record = data_j.get("record", False)
        check_path = data_j.get("check_path", False)
        debug = data_j.get("debug", False)
        extra_fonts = data_j.get("extra_fonts", None)

        if margins:
            appier.verify(
                isinstance(margins, (list, tuple)) and len(margins) == 4,
                message="Margins must be a 4-element array [left, right, top, bottom]",
            )

        # stages every extra font payload onto a per job temporary
        # directory so that gravo pilot can find the requested fonts
        # on disk by name and install them into the engraving software
        # for the duration of the print job, with a try and finally
        # block guaranteeing that the staging directory is removed
        # regardless of whether the print succeeds or raises
        extra_fonts_dir = None
        extra_fonts_paths = None
        if extra_fonts:
            extra_fonts_dir = tempfile.mkdtemp(prefix="colony-print-fonts-")
            extra_fonts_paths = self._stage_extra_fonts(extra_fonts, extra_fonts_dir)

        try:
            start = time.time()
            with gravo_pilot.capture_logs() as logs:
                screenshots = gravo_pilot.GravostyleAPI().write_text(
                    text,
                    font=font,
                    font_size=font_size,
                    width=width,
                    height=height,
                    margins=tuple(margins) if margins else None,
                    dry_run=dry_run,
                    record=record,
                    check_path=check_path,
                    extra_fonts=extra_fonts_paths,
                )
            duration = time.time() - start
        finally:
            if extra_fonts_dir:
                shutil.rmtree(extra_fonts_dir, ignore_errors=True)

        files = []

        for screenshot in screenshots:
            name, value = screenshot
            if appier.legacy.is_string(value):
                with open(value, "rb") as file:
                    data = file.read()
            else:
                buffer = appier.legacy.BytesIO()
                value.save(buffer, format="PNG")
                data = buffer.getvalue()
            _data_b64 = base64.b64encode(data)
            files.append(appier.File(dict(name=name, data=_data_b64)).json_v())

        return (
            dict(duration=duration, logs=logs, files=files)
            if debug
            else dict(duration=duration, files=files)
        )

    def _stage_extra_fonts(self, extra_fonts, target_dir):
        """
        Writes the provided extra fonts onto the given target directory
        as `<name>.f3s` files, returning the mapping of font name to
        the absolute path of the staged payload so that the caller can
        forward it to gravo pilot's `extra_fonts` keyword argument.

        Each entry value is a base64 string mirroring the wire format
        used by the rest of the gravo print payload, so that the print
        request itself stays as a single self contained JSON envelope.

        :type extra_fonts: dict
        :param extra_fonts: The mapping of font name to the base64
        encoded `.f3s` payload that should be staged on disk.
        :type target_dir: str
        :param target_dir: The file system path of the directory where
        the payloads should be written, typically a per job temporary
        directory owned by the caller.
        :rtype: dict
        :return: The mapping of font name to the absolute path of the
        staged payload, ready to be passed to gravo pilot.
        """

        paths = dict()
        for name, payload_b64 in extra_fonts.items():
            target_path = os.path.join(target_dir, "%s.f3s" % name)
            payload = base64.b64decode(payload_b64)
            with open(target_path, "wb") as file:
                file.write(payload)
            paths[name] = target_path
        return paths

    def _decode_payload(self, data_b64):
        """
        Decodes and parses the provided base64 encoded payload as JSON,
        returning the resulting structure to the caller.

        The decoded base64 data is converted to a text string before the
        JSON parsing so that the operation stays compatible with Python
        3.5, where the json.loads function does not accept byte input.

        :type data_b64: String
        :param data_b64: The base64 encoded payload to be decoded and
        parsed as a JSON structure.
        :rtype: Dictionary
        :return: The JSON structure parsed from the provided payload.
        """

        data = base64.b64decode(data_b64)
        return json.loads(data.decode("utf-8"))

    def _handle_text(self, data_b64):
        if not self._has_text():
            raise appier.OperationalError("text engine is not available")

        return dict(
            files=[appier.File(dict(name="document.txt", data=data_b64)).json_v()]
        )

    def _handle_fonts(self, data_b64):
        self._ensure_capability("dynamic-fonts")
        data_j = self._decode_payload(data_b64)
        return dict(fonts=self._install_fonts(data_j["fonts"]))

    def _handle_restart(self, job_id, update=False):
        """
        Requests the restart of the node for the job with the provided
        identifier, that is only done once the remaining jobs of the batch
        are printed and their results posted, so that no print is
        interrupted by it.

        For an update the boot is told (through the state file) to update
        the packages of the node when it starts again, even with the
        auto-update disabled, as a running node can't update itself.

        :type job_id: String
        :param job_id: The identifier of the job that requests the restart.
        :type update: bool
        :param update: If the packages of the node should be updated by
        the boot when the node starts again.
        """

        self._ensure_capability("update" if update else "restart")
        if update:
            self._save_state(NODE_UPDATE_ONCE="1")
        self.restart_jobs.append(job_id)

    def _handle_auto_update(self, options):
        self._ensure_capability("auto-update")
        enabled = options.get("enabled", None)
        appier.verify(
            isinstance(enabled, bool), message="Enabled must be a boolean value"
        )

        # keeps the auto-update in the state file, that is applied by the
        # boot (over the configuration) the next time the node starts
        self._save_state(NODE_UPDATE="1" if enabled else "0")
        self.node_update = enabled
        return dict(auto=enabled)

    def _build_font_cache(self):
        """
        Builds the cache of the fonts installed on demand of the node,
        using the configured path and maximum size of the fonts, loading
        the fonts already installed (in previous executions).

        An index of the cache that fails to load (eg: corrupted) is logged
        and the cache starts empty, so that the node keeps running.

        :rtype: FontCache
        :return: The font cache of the node, with its fonts loaded.
        """

        import colony_print

        # uses the configured path of the font cache, defaulting on windows
        # nodes to the data directory, the working directory of the service
        # (with its configuration), as their boot script may not set it
        fonts_path = appier.conf("FONTS_PATH", None)
        if not fonts_path and os.name == "nt" and os.path.isfile("config.env"):
            fonts_path = os.path.abspath("fonts")
        fonts_path = fonts_path or FONTS_PATH
        font_max_size = appier.conf(
            "FONT_MAX_SIZE", colony_print.FONT_MAX_SIZE, cast=int
        )
        font_cache = colony_print.FontCache(
            os.path.expanduser(fonts_path), max_size=font_max_size
        )
        try:
            font_cache.load()
        except Exception as exception:
            logging.warning(
                "Problem loading font cache '%s': %s"
                % (font_cache.path, str(exception))
            )
        return font_cache

    def _install_fonts(self, fonts):
        """
        Installs the provided fonts (entries of a job) in the font cache
        of the node, loading them in the system (when required) so that
        they're used in the printing of the documents.

        :type fonts: List
        :param fonts: The fonts (entries) to be installed.
        :rtype: List
        :return: The information of the installed fonts.
        """

        # installs the fonts in the font cache, loading the active fonts in
        # the system even when one of them fails, as the previous ones may
        # have been installed (becoming the active ones) in the meantime
        try:
            fonts = [self.font_cache.install(font) for font in fonts]
        finally:
            self._load_fonts()

        # verifies that the (active) fonts of the job are loaded in the
        # system (when it loads fonts), failing the job otherwise, as the
        # failures to load the fonts of the cache are only logged
        if self._has_npcolony() and self._has_feature("load-fonts"):
            file_paths = set(self.font_cache.files().values())
            for font in fonts:
                if not font["path"] in file_paths:
                    continue
                if font["path"] in self.loaded_fonts:
                    continue
                raise appier.OperationalError(
                    "Font '%s' not loaded in the system" % font["name"]
                )

        return fonts

    def _load_fonts(self):
        """
        Loads the fonts used (active) by the font cache in the system (the
        GDI of windows) through npcolony, unloading the ones loaded before
        that are no longer used, so that the system prints with them.

        The systems whose npcolony is not able to load fonts are left
        untouched, as the CUPS ones that embed the fonts in the PDF
        documents they print.

        A font that fails to (un)load is logged and doesn't prevent the
        other fonts from loading, the jobs that require it fail instead.
        """

        if not self._has_npcolony() or not self._has_feature("load-fonts"):
            return
        file_paths = set(self.font_cache.files().values())
        for file_path in sorted(self.loaded_fonts - file_paths):
            try:
                self.npcolony.unload_font(file_path)
            except Exception as exception:
                logging.warning(
                    "Problem unloading font '%s': %s" % (file_path, str(exception))
                )
            self.loaded_fonts.discard(file_path)
        for file_path in sorted(file_paths - self.loaded_fonts):
            try:
                self.npcolony.load_font(file_path)
            except Exception as exception:
                logging.warning(
                    "Problem loading font '%s': %s" % (file_path, str(exception))
                )
                continue
            self.loaded_fonts.add(file_path)

    def _restart(self):
        """
        Restarts the process of the node in the way the node is configured
        to, either by exiting with the (error) exit code reserved for it, so
        that the service of the node starts it again, or by running its own
        command line once more, replacing the process (that keeps its PID)
        or, where that's not possible (windows), starting a new process and
        exiting.

        The command line is the original one of the interpreter (with its
        options) where it's available (Python 3.10+), the one of the script
        being used otherwise, and it's run with the environment the process
        was started with, so that a changed configuration applies.
        """

        if not self.node_restart in RESTART_MODES:
            raise appier.OperationalError(
                message="Restart '%s' not valid" % self.node_restart
            )

        logging.info("Restarting node using '%s'" % self.node_restart)
        if self.node_restart == "exit":
            sys.exit(RESTART_CODE)

        args = sys.orig_argv[1:] if hasattr(sys, "orig_argv") else sys.argv
        args = [sys.executable] + list(args)
        environ = self._environ()
        if os.name == "nt":
            subprocess.Popen(args, env=environ)
            sys.exit(0)
        os.execve(sys.executable, args, environ)

    def _environ(self):
        """
        Builds the environment of the process that is run by the restart of
        the node, the one the process of the node was started with, meaning
        without the values set by the boot (the ones of the configuration
        file and the ones handed over to the node), as named by it, so that
        the boot applies the (possibly changed) configuration once more, as
        it does when it's started by the service.

        :rtype: Dictionary
        :return: The environment the process of the node was started with.
        """

        environ = dict(os.environ)
        keys = appier.conf("NODE_BOOT_KEYS", "")
        for key in keys.split(","):
            environ.pop(key, None)
        return environ

    def _save_state(self, **values):
        """
        Saves the provided values in the state file of the node, the one
        that is applied by the boot over the configuration (that is never
        written by the node, as it holds the secret key), keeping its other
        values and replacing the file atomically.
        """

        import colony_print.boot

        boot = colony_print.boot.ColonyPrintBoot()
        state = boot.load_config(self.node_state)
        state.update(values)
        boot.save_config(self.node_state, state)

    def _has_npcolony(self):
        try:
            __import__("npcolony")
        except Exception:
            return False
        return True

    def _has_gravo(self):
        try:
            __import__("gravo_pilot")
        except Exception:
            return False
        return True

    def _has_text(self):
        return True

    def _has_feature(self, feature):
        """
        Verifies if the provided (optional) feature of npcolony is supported
        in the current system, as reported by npcolony itself, the versions
        of npcolony that don't report their features support none of them.

        :type feature: String
        :param feature: The name of the feature of npcolony (eg: load-fonts).
        :rtype: bool
        :return: If the feature is supported by npcolony in the system.
        """

        if not hasattr(self.npcolony, "get_features"):
            return False
        return feature in self.npcolony.get_features()

    def _is_enabled(self, name, default="1"):
        """
        Verifies if the configuration with the provided name is enabled,
        meaning that its value is not one of the false ones, using the
        same rules as the boot of the node, so that both agree on it.

        :type name: String
        :param name: The name of the configuration (eg: NODE_CONTROL).
        :type default: String
        :param default: The value used when the configuration is not set.
        :rtype: bool
        :return: If the configuration is enabled.
        """

        value = appier.conf(name, default)
        return not str(value).strip().lower() in FALSE_VALUES

    def _info_npcolony(self):
        info = dict(
            format=self.npcolony.get_format(), devices=self.npcolony.get_devices()
        )
        if hasattr(self.npcolony, "VERSION"):
            info["version"] = self.npcolony.VERSION
        return info

    def _info_gravo(self):
        import gravo_pilot

        info = dict()
        if hasattr(gravo_pilot, "VERSION"):
            info["version"] = gravo_pilot.VERSION
        return info

    def _info_distribution(self):
        """
        Retrieves the description of the distribution of the operating
        system (eg: Ubuntu 24.04.1 LTS) from its os-release file, which
        only exists in linux systems.

        A file that can't be read is ignored, as this information is
        submitted by the loop of the node, that must not be stopped by it.

        :rtype: String
        :return: The description of the distribution, or an invalid
        value in case it's not available.
        """

        # uses only the first file that exists (os-release specification),
        # even if it has no description or can't be read, as the other
        # files are fallbacks only for when it's missing
        for path in OS_RELEASE_PATHS:
            if not os.path.isfile(path):
                continue
            try:
                with open(path, "rb") as file:
                    data = file.read().decode("utf-8")
            except Exception:
                return None
            for line in data.splitlines():
                key, _separator, value = line.partition("=")
                if not key.strip() == "PRETTY_NAME":
                    continue
                return value.strip().strip("\"'") or None
            return None
        return None

    def _ensure_format(self, format):
        # tries to make sure that the format is compatible with the current
        # system, this is required to avoid problems with the printing of the
        # data in printers of the current system, note that binie documents
        # are compatible with pdf systems as they are converted into pdf and
        # XMPL documents with every system as they are converted into binie
        if (
            format
            and hasattr(self.npcolony, "get_format")
            and not format == self.npcolony.get_format()
            and not (format == "binie" and self.npcolony.get_format() == "pdf")
            and not format == "xmpl"
        ):
            raise appier.OperationalError(
                "Format '%s' not compatible with system" % format
            )

    def _ensure_capability(self, capability):
        # makes sure that the capability is supported by the node (as
        # advertised), so that the jobs that require a capability the
        # node doesn't support fail instead of being wrongly printed
        if not capability in self.capabilities:
            raise appier.OperationalError(
                message="Capability '%s' not supported by node" % capability
            )


if __name__ == "__main__":
    node = ColonyPrintNode()
    node.loop()
else:
    __path__ = []
