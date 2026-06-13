#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import json
import uuid
import time
import base64

import appier

CLONE_FIELDS = set(
    [
        "name",
        "node_id",
        "printer",
        "data_length",
        "type",
        "format",
        "options",
    ]
)


class JobController(appier.Controller):
    @appier.route("/jobs", "GET", json=True)
    @appier.ensure(token="admin")
    def list(self):
        return dict(self.owner.jobs_info)

    @appier.route("/jobs", "OPTIONS")
    def list_o(self):
        return ""

    @appier.route("/jobs/<str:id>", "GET", json=True)
    @appier.ensure(token="admin")
    def show(self, id):
        return self.enrich_job_info(self.owner.jobs_info[id])

    @appier.route("/jobs/<str:id>", "OPTIONS")
    def show_o(self, id):
        return ""

    @appier.route("/jobs/<str:id>/cancel", "POST", json=True)
    @appier.ensure(token="admin")
    def cancel(self, id):
        appier.verify(
            id in self.owner.jobs_info,
            message="Job not found",
            code=404,
        )

        job_info = self.owner.jobs_info[id]
        status = job_info.get("status", None)

        # only queued jobs may be reliably cancelled, as a job already
        # picked up by a node is being printed and can no longer be
        # stopped from the server side
        appier.verify(
            status == "queued",
            message="Job in '%s' status can not be cancelled" % status,
            code=409,
        )

        # removes the job from the pending queue of its node so that it
        # is never dispatched, in case it has not been picked up yet
        node_id = job_info["node_id"]
        jobs = self.owner.jobs.get(node_id, [])
        self.owner.jobs[node_id] = [job for job in jobs if not job["id"] == id]

        job_info.update(status="cancelled", cancel_time=time.time())
        return job_info

    @appier.route("/jobs/<str:id>/cancel", "OPTIONS")
    def cancel_o(self, id):
        return ""

    @appier.route("/jobs/<str:id>/clone", "POST", json=True)
    @appier.ensure(token="admin")
    def clone(self, id):
        appier.verify(
            id in self.owner.jobs_info,
            message="Job not found",
            code=404,
        )

        # retrieves the original (base64 encoded) data that was persisted
        # at print time, as it is required to replicate the job exactly
        data_b64 = self.owner.jobs_data.get(id, None)
        appier.verify(
            not data_b64 == None,
            message="Job payload is no longer available",
            code=409,
        )

        # builds the clone job info as a copy of the original one keeping
        # only the static fields and assigning a new identifier so that
        # the clone starts its life cycle as a freshly queued job
        job_info = self.owner.jobs_info[id]
        job_id = str(uuid.uuid4())
        node_id = job_info["node_id"]
        clone_info = dict((k, v) for k, v in job_info.items() if k in CLONE_FIELDS)
        clone_info["id"] = job_id
        self.owner.jobs_info[job_id] = clone_info
        self.owner.jobs_data[job_id] = data_b64

        # creates a copy of the job info as starting
        # point for the job structure and then adds
        # the "heavy" data (base64 encoded) to it
        job = dict(clone_info)
        job["data_b64"] = data_b64
        jobs = self.owner.jobs.get(node_id, [])
        jobs.append(job)
        self.owner.jobs[node_id] = jobs
        appier.notify("jobs:%s" % node_id)

        clone_info.update(status="queued", queued_time=time.time())
        return clone_info

    @appier.route("/jobs/<str:id>/clone", "OPTIONS")
    def clone_o(self, id):
        return ""

    @appier.route("/jobs/<str:id>/files", "GET", json=True)
    @appier.ensure(token="admin")
    def files(self, id):
        data_path = appier.conf("DATA_PATH", "./data")
        job_path = os.path.join(data_path, id)
        if not os.path.isdir(job_path):
            return []
        return [
            dict(name=name, size=os.path.getsize(os.path.join(job_path, name)))
            for name in sorted(os.listdir(job_path))
        ]

    @appier.route("/jobs/<str:id>/files", "OPTIONS")
    def files_o(self, id):
        return ""

    @appier.route("/jobs/<str:id>/files/<str:name>", "GET")
    @appier.ensure(token="admin")
    def file(self, id, name):
        data_path = appier.conf("DATA_PATH", "./data")
        file_path = os.path.join(data_path, id, name)
        appier.verify(
            os.path.isfile(file_path),
            message="File not found",
            code=404,
        )
        return self.send_path(file_path)

    @appier.route("/jobs/<str:id>/files/<str:name>", "OPTIONS")
    def file_o(self, id, name):
        return ""

    @appier.route("/jobs/<str:id>/payload", "GET")
    @appier.ensure(token="admin")
    def payload(self, id):
        appier.verify(
            id in self.owner.jobs_data,
            message="Job payload not found",
            code=404,
        )

        # decodes the original (base64 encoded) data that was persisted
        # at print time so that it can be served as a downloadable file
        job_info = self.owner.jobs_info.get(id, dict())
        name = job_info.get("name", id)
        data = base64.b64decode(self.owner.jobs_data[id])
        return self.send_file(data, name="%s.payload" % name)

    @appier.route("/jobs/<str:id>/payload", "OPTIONS")
    def payload_o(self, id):
        return ""

    def enrich_job_info(self, job_info):
        # enriches a copy of the provided job info with the decoded request
        # payload pulled from the persisted data on demand, so that it is not
        # kept within the (listed) job info and the listing stays lean
        job_info = dict(job_info)
        data_b64 = self.owner.jobs_data.get(job_info["id"], None)
        request_payload = self._decode_payload(data_b64) if data_b64 else None
        if request_payload:
            job_info["request_payload"] = request_payload
        return job_info

    def _decode_payload(self, data_b64):
        """
        Tries to decode and parse the base64-encoded job data as JSON
        so it can be exposed as the request payload for inspection in
        the admin UI (e.g. gravo jobs contain text, font, width, height).
        Returns None for binary payloads that are not valid JSON.

        :type data_b64: String
        :param data_b64: The base64-encoded job data string.
        :rtype: Dictionary
        :return: The parsed JSON payload as a dictionary, or None
        if the data is not valid JSON (e.g. binary npcolony data).
        """

        try:
            data = base64.b64decode(data_b64)
            return json.loads(data)
        except Exception:
            return None
