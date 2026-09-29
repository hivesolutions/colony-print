#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import time
import uuid
import json
import base64
import shutil
import struct
import logging
import tempfile
import traceback

import appier

NAME = "colony-print"
""" The name of the program currently running """

VERSION = "0.20.0"
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

SIZE_TOLERANCE = 72.0 / 25.4
""" The tolerance (in points, one millimeter) of the comparison of
the size of a document with the size of the media of a printer and
with the limits of its custom sizes, as the sizes of the printers
are rounded (eg: to points) """

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

        logging.info("Booting %s %s (%s)" % (NAME, VERSION, appier.PLATFORM))
        logging.info("Running node '%s' in '%s' mode" % (node_id, self.node_mode))

        headers = dict()
        if secret_key:
            headers["X-Secret-Key"] = secret_key

        while True:
            try:
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
                        platform=appier.PLATFORM,
                        os=os.name,
                        version=VERSION,
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
        import mailme

        data_b64 = job["data_b64"]
        name = job.get("name", "undefined")
        printer = job.get("printer", None)
        format = job.get("format", None)
        options = job.get("options", dict())
        save_output = options.get("save_output", False)
        send_email = options.get("send_email", True)
        safe_sleep = options.get("safe_sleep", 0.0)
        printer_s = printer if printer else self.node_printer
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
                data_b64, format=format, printer=printer_s, options=options
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
            output_data=output_data_b64 if save_output else None,
            output_encoding="base64" if save_output else None,
            output_mime_type="application/pdf" if save_output else None,
        )

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

    def _handle_job(self, job):
        # unpacks the complete set of job information to
        # be able to print the job in the current system
        data_b64 = job["data_b64"]
        name = job.get("name", "undefined")
        printer = job.get("printer", None)
        type = job.get("type", None)
        format = job.get("format", None)
        options = job.get("options", dict())
        printer_s = printer if printer else self.node_printer

        logging.info("Printing job '%s' with '%s' printer" % (name, printer_s))
        if format:
            logging.info("Using format '%s' for job '%s'" % (format, name))

        if type in (None, "npcolony"):
            options["title"] = name
            result = self._handle_npcolony(
                data_b64, format=format, printer=printer_s, options=options
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

    def _handle_npcolony(self, data_b64, format=None, printer=None, options=dict()):
        if not self._has_npcolony():
            raise appier.OperationalError("npcolony engine is not available")

        # in case the data is a binie document and the current system only
        # prints pdf documents (eg: cups) converts the document into a pdf
        # one laid out for the printer, resulting in the same windows layout
        if self._is_binie(data_b64, format=format):
            data_b64, options = self._convert_binie(
                data_b64, printer=printer, options=options
            )
            format = "pdf"

        self._ensure_format(format)

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
        # the margins of the printer (or the custom size of the document),
        # an exception is raised in case the document is not valid
        renderer = colony_print.BinieRenderer(size=size, margins=margins, custom=custom)
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

    def _ensure_format(self, format):
        # tries to make sure that the format is compatible with the current
        # system, this is required to avoid problems with the printing of the
        # data in printers of the current system, note that binie documents
        # are compatible with pdf systems as they are converted into pdf
        if (
            format
            and hasattr(self.npcolony, "get_format")
            and not format == self.npcolony.get_format()
            and not (format == "binie" and self.npcolony.get_format() == "pdf")
        ):
            raise appier.OperationalError(
                "Format '%s' not compatible with system" % format
            )


if __name__ == "__main__":
    node = ColonyPrintNode()
    node.loop()
else:
    __path__ = []
