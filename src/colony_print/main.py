#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import base64

import appier
import appier_extras

COMMAND_TYPES = set(["restart", "update", "auto-update"])
""" The set of types of the jobs that are commands for the nodes (as
requested from the admin), instead of documents to be printed """

RESTART_TYPES = set(["restart", "update"])
""" The set of types of the (command) jobs that restart their node,
which are finished by the server once the (restarted) node registers
itself again, and not by a result of the node """


class ColonyPrintApp(appier.APIApp):
    def __init__(self, *args, **kwargs):
        appier.APIApp.__init__(
            self, name="colony-print", parts=(appier_extras.AdminPart,), *args, **kwargs
        )
        self.start_time = time.time()
        self.nodes = dict()
        self.jobs = dict()
        self.jobs_info = appier.LimitedSizeDict(
            max_size=appier.conf("JOB_SIZE", 128, cast=int)
        )
        self.jobs_data = appier.LimitedSizeDict(
            max_size=appier.conf("JOB_SIZE", 128, cast=int)
        )
        self.jobs_fonts = appier.LimitedSizeDict(
            max_size=appier.conf("JOB_SIZE", 128, cast=int)
        )

    def node_stats(self, id):
        """
        Computes the print statistics of the node with the provided
        identifier from the jobs retained by the server, the number
        of jobs (total and by status) and the last job to be finished.

        The finished jobs are only the ones for which the node has
        reported a success result, the other ones that have reached the
        finished status (with an error result or with no result at all)
        being counted as errored jobs, as there's no error status.

        The jobs that are commands for the node (eg: its restart) are
        left out of the statistics, as they print no document.

        :type id: String
        :param id: The identifier of the node to compute the statistics.
        :rtype: Dictionary
        :return: The print statistics of the node, with the last job
        only in case at least one of its jobs has been finished.
        """

        stats = dict(total=0, finished=0, error=0, in_flight=0, cancelled=0)
        last = None

        # iterates over the jobs of the node to count them by status, note
        # that these statistics are bounded by the jobs retained by the
        # server (JOB_SIZE, 128 by default), as the older ones are discarded
        for job_info in self.jobs_info.values():
            if not job_info.get("node_id", None) == id:
                continue
            if job_info.get("type", None) in COMMAND_TYPES:
                continue
            status = job_info.get("status", None)
            result = job_info.get("result", None) or dict()
            stats["total"] += 1
            if status in ("queued", "printing"):
                stats["in_flight"] += 1
            elif status == "cancelled":
                stats["cancelled"] += 1
            elif status == "finished" and result.get("result", None) == "success":
                stats["finished"] += 1
            elif status == "finished":
                stats["error"] += 1

            # keeps the finished job with the most recent finish time
            # as the last job of the node (the last one to be printed)
            if not status == "finished":
                continue
            if last and last.get("finish_time", 0) > job_info.get("finish_time", 0):
                continue
            last = job_info

        if last:
            result = last.get("result", None) or dict()
            stats["last"] = dict(
                id=last.get("id", None),
                name=last.get("name", None),
                finish_time=last.get("finish_time", None),
                result=result.get("result", None),
            )
        return stats

    def queue_job(self, job_info, data_b64=None, fonts=None):
        """
        Queues the job with the provided information for its node, keeping
        its information, its (base64 encoded) data and its fonts, so that
        they're dropped together, and notifying the node (that is waiting
        for its jobs).

        The job that is sent to the node is a copy of its information with
        the "heavy" data (base64 encoded) added to it and with the fonts
        of the request replacing their (light) information, as the node
        installs them, the jobs that are commands having no data.

        The fonts are not sent to a (known) node that doesn't support them,
        that prints the document with its own fonts, the fonts of the job
        being marked as skipped (and removed from its XMPL document), which
        is decided whenever the job is queued (eg: a clone of the job once
        the node supports the fonts).

        :type job_info: Dictionary
        :param job_info: The information of the job, with its identifier
        and the one of its node.
        :type data_b64: String
        :param data_b64: The base64 encoded data of the job, if any.
        :type fonts: List
        :param fonts: The fonts (entries) of the job, if any.
        :rtype: Dictionary
        :return: The information of the job, that is now queued.
        """

        import colony_print

        job_id = job_info["id"]
        node_id = job_info["node_id"]

        # in case the node is known not to support the fonts (eg: an older
        # node) the fonts of the job are skipped, the unknown nodes (eg: not
        # registered since the server restarted) receiving them, as they're
        # skipped by the nodes that don't support them
        skipped = self.fonts_skipped(job_info)
        if skipped:
            job_info["fonts_skipped"] = True

        self.jobs_info[job_id] = job_info
        self.jobs_data[job_id] = data_b64
        self.jobs_fonts[job_id] = fonts

        job = dict(job_info)
        if not data_b64 == None:
            job["data_b64"] = data_b64
        job.pop("fonts", None)
        if fonts and not skipped:
            job["fonts"] = fonts

        # removes the fonts declared by the XMPL document of a job whose fonts
        # are skipped, from the document sent to the node, as the nodes that
        # don't skip the fonts they don't support (older versions) would fail
        # the document, the document of the job being kept untouched
        if skipped and job_info.get("format", None) == "xmpl":
            data = colony_print.strip_xmpl_fonts(base64.b64decode(data_b64))
            job["data_b64"] = base64.b64encode(data).decode("utf-8")

        jobs = self.jobs.get(node_id, [])
        jobs.append(job)
        self.jobs[node_id] = jobs
        appier.notify("jobs:%s" % node_id)

        job_info.update(status="queued", queued_time=time.time())
        return job_info

    def fonts_skipped(self, job_info):
        """
        Verifies if the fonts of the job with the provided information are
        skipped for its node, as the node is known not to support the fonts
        (eg: an older node), the unknown nodes being considered to support
        them, as the nodes that don't support them skip them.

        The jobs of the fonts type (installations) and the jobs without fonts
        have no fonts to be skipped.

        :type job_info: Dictionary
        :param job_info: The information of the job, with the (light)
        information of its fonts and the identifier of its node.
        :rtype: bool
        :return: If the fonts of the job are skipped for its node, that
        prints its document with its own fonts.
        """

        node = self.nodes.get(job_info["node_id"], None)
        if not node or not job_info.get("fonts", None):
            return False
        if job_info.get("type", None) == "fonts":
            return False
        return not "dynamic-fonts" in node.get("capabilities", [])

    def _version(self):
        return "0.23.0"

    def _description(self):
        return "Colony Print"

    def _observations(self):
        return "Printing in the cloud"


if __name__ == "__main__":
    app = ColonyPrintApp()
    app.serve()
else:
    __path__ = []
