#!/usr/bin/python
# -*- coding: utf-8 -*-

import logging
import unittest

import appier

import colony_print


class ColonyPrintAppTest(unittest.TestCase):
    def setUp(self):
        self.app = colony_print.ColonyPrintApp(level=logging.ERROR)
        self.notifications = []
        self._notify = appier.notify
        appier.notify = lambda name, *args, **kwargs: self.notifications.append(name)

    def tearDown(self):
        appier.notify = self._notify
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
        self.app.jobs_info["invalid"] = dict(
            id="invalid",
            name="invalid",
            node_id="node",
            status="finished",
            finish_time=50.0,
            result=dict(result="unknown"),
        )
        self.app.jobs_info["unknown"] = dict(id="unknown", node_id="node")

        # the jobs finished without a success result have not been printed
        # (eg: the ones of a type not handled by the node, that have an
        # empty result), so they are counted as errored and not as finished
        stats = self.app.node_stats("node")
        self.assertEqual(stats["total"], 4)
        self.assertEqual(stats["finished"], 0)
        self.assertEqual(stats["error"], 3)
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

    def test_node_stats_commands(self):
        # the jobs that are commands for the node (eg: its restart) print no
        # document, so they are left out of its statistics (and are never
        # its last job), whatever their status is
        self.app.jobs_info["success"] = dict(
            id="success",
            name="success",
            node_id="node",
            status="finished",
            finish_time=100.0,
            result=dict(result="success"),
        )
        for index, type in enumerate(("restart", "update", "auto-update")):
            self.app.jobs_info[type] = dict(
                id=type,
                name=type,
                node_id="node",
                type=type,
                status="finished",
                finish_time=200.0 + index,
                result=dict(result="error" if type == "update" else "success"),
            )
        for status in ("queued", "printing", "cancelled"):
            self.app.jobs_info[status] = dict(
                id=status, name="restart", node_id="node", type="restart", status=status
            )
        self.assertEqual(
            self.app.node_stats("node"),
            dict(
                total=1,
                finished=1,
                error=0,
                in_flight=0,
                cancelled=0,
                last=dict(
                    id="success", name="success", finish_time=100.0, result="success"
                ),
            ),
        )

        # the jobs of the other types (eg: the installation of fonts) are
        # part of the statistics, as before
        self.app.jobs_info["fonts"] = dict(
            id="fonts", name="fonts", node_id="node", type="fonts", status="queued"
        )
        stats = self.app.node_stats("node")
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["in_flight"], 1)

    def test_queue_job(self):
        # the job is kept (its information, its data and its fonts) and sent
        # to its node with the data and with the fonts of the request in the
        # place of their information, the node being notified about it
        fonts = [dict(name="Colonia", data_b64="QUJD")]
        job_info = dict(
            id="first",
            name="document",
            node_id="node",
            data_length=4,
            format="binie",
            fonts=[dict(name="Colonia", data_length=4)],
        )
        result = self.app.queue_job(job_info, data_b64="QUJD", fonts=fonts)
        self.assertEqual(result is job_info, True)
        self.assertEqual(job_info["status"], "queued")
        self.assertEqual(type(job_info["queued_time"]), float)
        self.assertEqual(job_info["fonts"], [dict(name="Colonia", data_length=4)])
        self.assertEqual(self.app.jobs_info["first"] is job_info, True)
        self.assertEqual(self.app.jobs_data["first"], "QUJD")
        self.assertEqual(self.app.jobs_fonts["first"], fonts)
        self.assertEqual(
            self.app.jobs["node"],
            [
                dict(
                    id="first",
                    name="document",
                    node_id="node",
                    data_length=4,
                    format="binie",
                    data_b64="QUJD",
                    fonts=fonts,
                )
            ],
        )
        self.assertEqual(self.notifications, ["jobs:node"])

        # a job without fonts is sent without them, even when it keeps
        # their information (the fonts declared by its document)
        job_info = dict(
            id="second",
            name="document",
            node_id="node",
            fonts=[dict(name="Colonia", data_length=4)],
        )
        self.app.queue_job(job_info, data_b64="QUJD")
        self.assertEqual(self.app.jobs_fonts["second"], None)
        self.assertEqual(
            self.app.jobs["node"][1],
            dict(id="second", name="document", node_id="node", data_b64="QUJD"),
        )

        # a job that is a command has no data (nor fonts), but is kept as
        # the other jobs, so that their structures are dropped together
        job_info = dict(id="third", name="restart", node_id="node", type="restart")
        self.app.queue_job(job_info)
        self.assertEqual(self.app.jobs_data["third"], None)
        self.assertEqual(self.app.jobs_fonts["third"], None)
        self.assertEqual(
            self.app.jobs["node"][2],
            dict(id="third", name="restart", node_id="node", type="restart"),
        )
        self.assertEqual(
            [job["id"] for job in self.app.jobs["node"]], ["first", "second", "third"]
        )
        self.assertEqual(
            sorted(self.app.jobs_info.keys()), sorted(self.app.jobs_data.keys())
        )

        # the jobs are queued for their own node
        job_info = dict(id="fourth", name="document", node_id="other")
        self.app.queue_job(job_info, data_b64="QUJD")
        self.assertEqual([job["id"] for job in self.app.jobs["other"]], ["fourth"])
        self.assertEqual(len(self.app.jobs["node"]), 3)
        self.assertEqual(self.notifications[-1], "jobs:other")
        self.assertEqual(len(self.notifications), 4)
