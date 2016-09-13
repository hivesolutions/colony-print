#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging

import appier

BASE_URL = "https://print.bemisc.com/"

class ColonyPrintNode(object):

    def loop(self):
        logging.basicConfig(level = logging.DEBUG)

        base_url = appier.conf("BASE_URL", BASE_URL)
        node_id = appier.conf("NODE_ID", "node")
        node_name = appier.conf("NODE_NAME", "node")
        node_location = appier.conf("NODE_LOCATION", "undefined")

        while True:
            logging.info("Submitting node information")
            appier.post(
                base_url + "nodes/%s" % node_id,
                data_j = dict(
                    name = node_name,
                    location = node_location
                )
            )
            logging.info("Retrieving jobs for node '%s'" % node_id)
            jobs = appier.get(base_url + "nodes/%s/jobs" % node_id)
            logging.info("Retrieved %d jobs for node '%s'" % (len(jobs), node_id))
            for job in jobs: self.print_job(job)

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
