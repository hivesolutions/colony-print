#!/usr/bin/python
# -*- coding: utf-8 -*-

import time

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

        job_id = job_info["id"]
        node_id = job_info["node_id"]
        self.jobs_info[job_id] = job_info
        self.jobs_data[job_id] = data_b64
        self.jobs_fonts[job_id] = fonts

        job = dict(job_info)
        if not data_b64 == None:
            job["data_b64"] = data_b64
        job.pop("fonts", None)
        if fonts:
            job["fonts"] = fonts
        jobs = self.jobs.get(node_id, [])
        jobs.append(job)
        self.jobs[node_id] = jobs
        appier.notify("jobs:%s" % node_id)

        job_info.update(status="queued", queued_time=time.time())
        return job_info

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
