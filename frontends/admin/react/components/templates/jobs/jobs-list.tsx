import React, { FC, useCallback, useEffect, useMemo, useState } from "react";

import { useAPI } from "../../../hooks";
import { JobInfo } from "../../../api/colony-print";
import { Button, Tag } from "../../atoms";
import { ContentHeader, DataTable } from "../../molecules";
import { formatTimestamp } from "../../../utils";

import "./jobs-list.css";

type StatusFilter = "all" | "queued" | "printing" | "finished";

export const JobsList: FC = () => {
    const api = useAPI();
    const [jobs, setJobs] = useState<JobInfo[]>([]);
    const [loading, setLoading] = useState(true);
    const [filter, setFilter] = useState<StatusFilter>("all");

    const fetchJobs = useCallback(async () => {
        setLoading(true);
        try {
            const data = await api.listJobs();
            const items = Object.values(data).sort(
                (a, b) => (b.queued_time || 0) - (a.queued_time || 0)
            );
            setJobs(items);
        } catch {
            setJobs([]);
        } finally {
            setLoading(false);
        }
    }, [api]);

    useEffect(() => {
        fetchJobs();
    }, [fetchJobs]);

    const filteredJobs = useMemo(
        () =>
            filter === "all"
                ? jobs
                : jobs.filter((j) => j.status === filter),
        [jobs, filter]
    );

    const columns = [
        {
            key: "id",
            header: "ID",
            render: (job: JobInfo) =>
                job.id ? job.id.substring(0, 8) + "..." : "-"
        },
        {
            key: "name",
            header: "Name",
            render: (job: JobInfo) => job.name || "-"
        },
        {
            key: "node_id",
            header: "Node",
            render: (job: JobInfo) => job.node_id
        },
        {
            key: "status",
            header: "Status",
            render: (job: JobInfo) => {
                const variant =
                    job.status === "finished"
                        ? "success"
                        : job.status === "printing"
                          ? "warning"
                          : "default";
                return (
                    <Tag
                        variant={
                            variant as
                                | "success"
                                | "warning"
                                | "default"
                        }
                    >
                        {job.status}
                    </Tag>
                );
            }
        },
        {
            key: "type",
            header: "Type",
            render: (job: JobInfo) => job.type || "-"
        },
        {
            key: "format",
            header: "Format",
            render: (job: JobInfo) => job.format || "-"
        },
        {
            key: "queued_time",
            header: "Queued",
            render: (job: JobInfo) => formatTimestamp(job.queued_time)
        },
        {
            key: "finish_time",
            header: "Finished",
            render: (job: JobInfo) => formatTimestamp(job.finish_time)
        }
    ];

    const filters: StatusFilter[] = [
        "all",
        "queued",
        "printing",
        "finished"
    ];

    return (
        <div className="jobs-list">
            <ContentHeader
                title="Jobs"
                description="Print jobs across all nodes"
                actions={
                    <Button
                        variant="secondary"
                        size="sm"
                        onClick={fetchJobs}
                    >
                        Refresh
                    </Button>
                }
            />
            <div className="jobs-list-filters">
                {filters.map((f) => (
                    <Button
                        key={f}
                        variant={filter === f ? "primary" : "secondary"}
                        size="sm"
                        onClick={() => setFilter(f)}
                    >
                        {f.charAt(0).toUpperCase() + f.slice(1)}
                    </Button>
                ))}
            </div>
            <DataTable
                columns={columns}
                data={filteredJobs}
                loading={loading}
                emptyMessage="No jobs found"
            />
        </div>
    );
};
