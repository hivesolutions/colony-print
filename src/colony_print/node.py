#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import logging

import appier

BASE_URL = "https://print.bemisc.com/"

SLEEP_TIME = 3.0

class ColonyPrintNode(object):

    def __init__(self, sleep_time = SLEEP_TIME):
        self.sleep_time = sleep_time

    def loop(self):
        logging.basicConfig(
            format = "%(asctime)s [%(levelname)s] %(message)s",
            level = logging.DEBUG
        )

        base_url = appier.conf("BASE_URL", BASE_URL)
        secret_key = appier.conf("SECRET_KEY", None)
        node_id = appier.conf("NODE_ID", "node")
        node_name = appier.conf("NODE_NAME", "node")
        node_location = appier.conf("NODE_LOCATION", "undefined")

        headers = dict()
        if secret_key: headers["X-Secret-Key"] = secret_key

        while True:
            try:
                logging.info("Submitting node information")
                appier.post(
                    base_url + "nodes/%s" % node_id,
                    data_j = dict(
                        name = node_name,
                        location = node_location
                    ),
                    headers = headers
                )
                logging.info("Retrieving jobs for node '%s'" % node_id)
                jobs = appier.get(
                    base_url + "nodes/%s/jobs" % node_id,
                    headers = headers,
                    timeout = 600
                )
                logging.info("Retrieved %d jobs for node '%s'" % (len(jobs), node_id))
                for job in jobs: self.print_job(job)
            except Exception as exception:
                logging.info("Exception while looping '%s'" % str(exception))
                logging.info("Sleeping for %.2f seconds" % self.sleep_time)
                time.sleep(self.sleep_time)

    def print_job(self, job):
        data_b64 = job["data_b64"]
        name = job.get("name", "undefined")
        printer = job.get("printer", None)
        printer_s = printer if printer else "default"
        logging.info("Printing job '%s' with '%s' printer" % (name, printer_s))
        if printer: self.npcolony.print_printer_base64(printer, data_b64)
        else: self.npcolony.print_base64(data_b64)

    @property
    def npcolony(self):
        import npcolony
        return npcolony

if __name__ == "__main__":
    node = ColonyPrintNode()
    node.loop()
else:
    __path__ = []
