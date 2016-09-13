#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging

import appier

BASE_URL = "https://colony_print.bemisc.com/"

def loop():
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

if __name__ == "__main__":
    loop()
