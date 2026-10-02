#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import unittest

import appier

import colony_print


class NodeControllerTest(unittest.TestCase):
    def setUp(self):
        self.app = colony_print.ColonyPrintApp(level=logging.ERROR)

    def tearDown(self):
        self.app.unload()
        adapter = appier.get_adapter()
        adapter.drop_db()

    def test_show(self):
        response = self.app.get("/nodes/name")
        self.assertEqual(response.code, 403)

    def test_print_default(self):
        response = self.app.get("/nodes/name/print")
        self.assertEqual(response.code, 403)

    def test_print_default_o(self):
        response = self.app.options("/nodes/name/print")
        self.assertEqual(response.code, 200)
        self.assertEqual(
            response.headers["Access-Control-Allow-Origin"].startswith("*"), True
        )
        self.assertEqual(
            response.headers["Access-Control-Allow-Headers"].startswith("*"), True
        )

    def test_valid_options(self):
        valid_options = colony_print.controllers.node.VALID_OPTIONS
        self.assertEqual("media" in valid_options, True)
        self.assertEqual("scaling" in valid_options, True)
        self.assertEqual("title" in valid_options, False)
        self.assertEqual("output_path" in valid_options, False)

    def test_enrich_node_includes_stats(self):
        controller = colony_print.controllers.NodeController(self.app)
        self.app.nodes["name"] = dict(name="Node", libraries=dict(appier="1.0.0"))
        self.app.jobs_info["first"] = dict(
            id="first",
            name="document",
            node_id="name",
            status="finished",
            finish_time=100.0,
            result=dict(result="success"),
        )
        self.app.jobs_info["second"] = dict(
            id="second", name="document", node_id="other", status="queued"
        )
        node = controller.enrich_node("name", self.app.nodes["name"])
        self.assertEqual(node["name"], "Node")
        self.assertEqual(node["libraries"], dict(appier="1.0.0"))
        self.assertEqual(
            node["stats"],
            dict(
                total=1,
                finished=1,
                error=0,
                in_flight=0,
                cancelled=0,
                last=dict(
                    id="first", name="document", finish_time=100.0, result="success"
                ),
            ),
        )
        self.assertEqual("stats" in self.app.nodes["name"], False)

    def test_enrich_node_without_jobs(self):
        controller = colony_print.controllers.NodeController(self.app)
        node = controller.enrich_node("name", dict(name="Node"))
        self.assertEqual(
            node,
            dict(
                name="Node",
                stats=dict(total=0, finished=0, error=0, in_flight=0, cancelled=0),
            ),
        )
