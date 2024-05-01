#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import time
import uuid
import base64
import shutil
import logging
import tempfile

import appier

BASE_URL = "https://print.bemisc.com/"
""" The default base URL to be used for the communication with the
Colony Print server """

SLEEP_TIME = 3.0
""" The default time to sleep between each iteration, this value
is used to avoid overloading the server with requests """

NODE_MODES = set(["normal", "email"])
""" The set of running modes that are considered to be valid for
the node, this is going to be used to validate the mode """


class ColonyPrintNode(object):
    def __init__(self, sleep_time=SLEEP_TIME):
        self.sleep_time = sleep_time
        self.node_mode = None
        self.node_email_address = None

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
        self.node_email_address = appier.conf("NODE_EMAIL_ADDRESS", "normal")

        headers = dict()
        if secret_key:
            headers["X-Secret-Key"] = secret_key

        while True:
            try:
                logging.info("Submitting node information")
                appier.post(
                    base_url + "nodes/%s" % node_id,
                    data_j=dict(name=node_name, location=node_location),
                    headers=headers,
                )
                logging.info("Retrieving jobs for node '%s'" % node_id)
                jobs = appier.get(
                    base_url + "nodes/%s/jobs" % node_id, headers=headers, timeout=600
                )
                logging.info("Retrieved %d jobs for node '%s'" % (len(jobs), node_id))
                for job in jobs:
                    self.print_job(job)
            except Exception as exception:
                logging.info("Exception while looping '%s'" % str(exception))
                logging.info("Sleeping for %.2f seconds" % self.sleep_time)
                time.sleep(self.sleep_time)

    def print_job(self, job):
        if not self.node_mode in NODE_MODES:
            raise appier.OperationalError("Mode '%s' not valid" % self.node_mode)
        return getattr(self, "print_job_" + self.node_mode)(job)

    def print_job_normal(self, job):
        # unpacks the complete set of job information to
        # be able to print the job in the current system
        data_b64 = job["data_b64"]
        name = job.get("name", "undefined")
        printer = job.get("printer", None)
        format = job.get("format", None)
        options = job.get("options", dict())
        printer_s = printer if printer else "default"

        self._ensure_format(format)

        logging.info("Printing job '%s' with '%s' printer" % (name, printer_s))
        if printer:
            self.npcolony.print_printer_base64(printer, data_b64, options=options)
        else:
            self.npcolony.print_base64(data_b64)

    def print_job_email(self, job):
        import mailme

        data_b64 = job["data_b64"]
        name = job.get("name", "undefined")
        printer = job.get("printer", None)
        format = job.get("format", None)
        options = job.get("options", dict())
        printer_s = printer if printer else "default"

        self._ensure_format(format)

        temp_dir = tempfile.mkdtemp()
        try:
            output_path = os.path.join(temp_dir, "%s.pdf" % str(uuid.uuid4()))
            options["output_path"] = output_path
            logging.info(
                "Generating document job '%s' with '%s' printer" % (name, printer_s)
            )
            if printer:
                self.npcolony.print_printer_base64(printer, data_b64, options=options)

            file = open(output_path, "rb")
            try:
                data = file.read()
            finally:
                file.close()

            receivers = [options.get("email_address", self.node_email_address)]
            logging.info(
                "Sending email to %s for job '%s' with '%s' printer"
                % (",".join(receivers), name, printer_s)
            )

            api = mailme.API()
            api.send(
                mailme.MessagePayload(
                    receivers=receivers,
                    subject="Print job '%s'" % name,
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

    @property
    def npcolony(self):
        import npcolony

        return npcolony

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
