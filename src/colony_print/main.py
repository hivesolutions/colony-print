#!/usr/bin/python
# -*- coding: utf-8 -*-

import time

import appier
import appier_extras


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
