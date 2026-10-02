#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import unittest

import appier

import colony_print


class ColonyPrintAppTest(unittest.TestCase):
    def setUp(self):
        self.app = colony_print.ColonyPrintApp(level=logging.ERROR)

    def tearDown(self):
        self.app.unload()
        adapter = appier.get_adapter()
        adapter.drop_db()

    def test_node_stats(self):
        self.app.jobs_info["queued"] = dict(
            id="queued", name="queued", node_id="node", status="queued"
        )
        self.app.jobs_info["printing"] = dict(
            id="printing", name="printing", node_id="node", status="printing"
        )
        self.app.jobs_info["cancelled"] = dict(
            id="cancelled", name="cancelled", node_id="node", status="cancelled"
        )
        self.app.jobs_info["success"] = dict(
            id="success",
            name="success",
            node_id="node",
            status="finished",
            finish_time=100.0,
            result=dict(result="success", handler="npcolony"),
        )
        self.app.jobs_info["error"] = dict(
            id="error",
            name="error",
            node_id="node",
            status="finished",
            finish_time=50.0,
            result=dict(result="error", error="boom"),
        )
        self.assertEqual(
            self.app.node_stats("node"),
            dict(
                total=5,
                finished=1,
                error=1,
                in_flight=2,
                cancelled=1,
                last=dict(
                    id="success", name="success", finish_time=100.0, result="success"
                ),
            ),
        )

    def test_node_stats_empty(self):
        self.assertEqual(
            self.app.node_stats("node"),
            dict(total=0, finished=0, error=0, in_flight=0, cancelled=0),
        )

        self.app.jobs_info["queued"] = dict(
            id="queued", name="queued", node_id="node", status="queued"
        )
        self.assertEqual(
            self.app.node_stats("node"),
            dict(total=1, finished=0, error=0, in_flight=1, cancelled=0),
        )

    def test_node_stats_other_nodes(self):
        self.app.jobs_info["first"] = dict(
            id="first",
            name="first",
            node_id="node",
            status="finished",
            finish_time=100.0,
            result=dict(result="success"),
        )
        self.app.jobs_info["second"] = dict(
            id="second",
            name="second",
            node_id="other",
            status="finished",
            finish_time=200.0,
            result=dict(result="error"),
        )
        self.app.jobs_info["third"] = dict(id="third", name="third", status="queued")
        stats = self.app.node_stats("node")
        self.assertEqual(stats["total"], 1)
        self.assertEqual(stats["finished"], 1)
        self.assertEqual(stats["error"], 0)
        self.assertEqual(stats["last"]["id"], "first")

        stats = self.app.node_stats("other")
        self.assertEqual(stats["total"], 1)
        self.assertEqual(stats["finished"], 0)
        self.assertEqual(stats["error"], 1)
        self.assertEqual(stats["last"]["id"], "second")

        stats = self.app.node_stats("missing")
        self.assertEqual(stats["total"], 0)
        self.assertEqual("last" in stats, False)

    def test_node_stats_last(self):
        self.app.jobs_info["newest"] = dict(
            id="newest",
            name="invoice",
            node_id="node",
            status="finished",
            finish_time=300.0,
            result=dict(result="error", error="boom", traceback="Traceback ..."),
        )
        self.app.jobs_info["oldest"] = dict(
            id="oldest",
            name="receipt",
            node_id="node",
            status="finished",
            finish_time=100.0,
            result=dict(result="success"),
        )
        self.app.jobs_info["printing"] = dict(
            id="printing",
            name="label",
            node_id="node",
            status="printing",
            printing_time=400.0,
        )
        self.app.jobs_info["cancelled"] = dict(
            id="cancelled",
            name="label",
            node_id="node",
            status="cancelled",
            cancel_time=500.0,
        )
        stats = self.app.node_stats("node")
        self.assertEqual(
            stats["last"],
            dict(id="newest", name="invoice", finish_time=300.0, result="error"),
        )

        self.app.jobs_info["oldest"].update(finish_time=600.0)
        stats = self.app.node_stats("node")
        self.assertEqual(
            stats["last"],
            dict(id="oldest", name="receipt", finish_time=600.0, result="success"),
        )

    def test_node_stats_no_result(self):
        self.app.jobs_info["empty"] = dict(
            id="empty",
            name="empty",
            node_id="node",
            status="finished",
            finish_time=100.0,
            result=dict(),
        )
        self.app.jobs_info["missing"] = dict(
            id="missing", name="missing", node_id="node", status="finished"
        )
        self.app.jobs_info["unknown"] = dict(id="unknown", node_id="node")
        stats = self.app.node_stats("node")
        self.assertEqual(stats["total"], 3)
        self.assertEqual(stats["finished"], 2)
        self.assertEqual(stats["error"], 0)
        self.assertEqual(stats["in_flight"], 0)
        self.assertEqual(
            stats["last"],
            dict(id="empty", name="empty", finish_time=100.0, result=None),
        )

    def test_node_stats_retained(self):
        # the statistics are bounded by the jobs retained by the server,
        # so the jobs that have been discarded are no longer counted
        self.app.jobs_info = appier.LimitedSizeDict(max_size=2)
        for index in range(3):
            self.app.jobs_info["job-%d" % index] = dict(
                id="job-%d" % index,
                name="job-%d" % index,
                node_id="node",
                status="finished",
                finish_time=100.0 - index,
                result=dict(result="success"),
            )
        stats = self.app.node_stats("node")
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["finished"], 2)
        self.assertEqual(stats["last"]["id"], "job-1")
