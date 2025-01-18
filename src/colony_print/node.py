#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import sys
import time
import uuid
import json
import base64
import shutil
import logging
import tempfile

import appier

NAME = "colony-print"
""" The name of the program currently running """

VERSION = "0.4.1"
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

EMAIL_TEMPLATE = """
Hey there!

Great news — your document **#%s** has just gone through a virtual transformation and is now rocking the PDF stage! 🎸📄 Ready to take a look? Check out the attachment—it's dressed to impress.

We hope you find everything in perfect harmony. Should you need a replay, just hit 'print' again!

Keep on printing,

Your's dear 'Colony Print'

P.S. No trees were harmed in the making of this PDF. 🌳✌️
"""


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
                        result = dict(result="error", error=str(exception))
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
                if os.path.exists(output_path):
                    break
                time.sleep(0.5)

            file = open(output_path, "rb")
            try:
                data = file.read()
            finally:
                file.close()

            # computes the complete list of email receivers using the
            # base instance value and the ones provided via options,
            # makes sure that the email receivers are unique
            email_receivers = list(self.node_email_receivers)
            email_receiver = options.get("email_receiver", None)
            if email_receiver:
                email_receivers += [email_receiver]
            email_receivers += options.get("email_receivers", [])
            email_receivers = list(set(email_receivers))

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
                    subject="Print Job #%s is Ready!" % short_name,
                    contents=EMAIL_TEMPLATE % name,
                    attachments=[
                        mailme.AttachmentPayload(
                            name="%s.pdf" % name,
                            data=base64.b64encode(data).decode(),
                            mime="application/pdf",
                        )
                    ],
                )
            )
        finally:
            shutil.rmtree(temp_dir)

        return dict(
            result="success",
            mode="email",
            handler="npcolony",
            email_sent=True,
            receivers=email_receivers,
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

        self._ensure_format(format)

        if printer:
            self.npcolony.print_printer_base64(printer, data_b64, options=options)
        else:
            self.npcolony.print_base64(data_b64)

        return dict()

    def _handle_gravo(self, data_b64):
        if not self._has_gravo():
            raise appier.OperationalError("gravo engine is not available")

        import gravo_pilot

        data = base64.b64decode(data_b64)
        data_j = json.loads(data)

        text = data_j["text"]
        font = data_j.get("font", "HELVETICA 1L")
        font_size = data_j.get("font_size", None)
        dry_run = data_j.get("dry_run", False)

        start = time.time()
        screenshots = gravo_pilot.GravostyleAPI().write_text(
            text, font=font, font_size=font_size, dry_run=dry_run
        )
        duration = time.time() - start

        files = []

        for screenshot in screenshots:
            name, image = screenshot
            buffer = appier.legacy.BytesIO()
            image.save(buffer, format="PNG")
            data = buffer.getvalue()
            _data_b64 = base64.b64encode(data)
            files.append(appier.File(dict(name=name, data=_data_b64)).json_v())

        return dict(duration=duration, files=files)

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
        return dict(
            format=self.npcolony.get_format(), devices=self.npcolony.get_devices()
        )

    def _ensure_format(self, format):
        # tries to make sure that the format is compatible with the current
        # system, this is required to avoid problems with the printing of the
        # data in printers of the current system
        if (
            format
            and hasattr(self.npcolony, "get_format")
            and not format == self.npcolony.get_format()
        ):
            raise appier.OperationalError(
                "Format '%s' not compatible with system" % format
            )


if __name__ == "__main__":
    node = ColonyPrintNode()
    node.loop()
else:
    __path__ = []
