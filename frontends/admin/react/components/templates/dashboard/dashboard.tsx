import React, { FC, useCallback, useEffect, useState } from "react";

import { useAPI } from "../../../hooks";
import { NodeInfo, JobInfo } from "../../../api/colony-print";
import { Tag } from "../../atoms";
import { ContentHeader, StatCard, DataTable } from "../../molecules";
import { formatRelativeTime } from "../../../utils";

import "./dashboard.css";

export const Dashboard: FC = () => {
    const api = useAPI();
    const [nodes, setNodes] = useState<Record<string, NodeInfo>>({});
    const [jobs, setJobs] = useState<Record<string, JobInfo>>({});
    const [healthy, setHealthy] = useState<boolean | null>(null);
    const [loading, setLoading] = useState(true);

    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            const [nodesData, jobsData, pingData] = await Promise.all([
                api.listNodes().catch(() => ({})),
                api.listJobs().catch(() => ({})),
                api.ping().catch(() => null)
            ]);
            setNodes(nodesData);
            setJobs(jobsData);
            setHealthy(pingData !== null);
        } finally {
            setLoading(false);
        }
    }, [api]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const nodeCount = Object.keys(nodes).length;
    const jobCount = Object.keys(jobs).length;
    const recentJobs = Object.values(jobs)
        .sort((a, b) => (b.queued_time || 0) - (a.queued_time || 0))
        .slice(0, 10);

    const columns = [
        {
            key: "name",
            header: "Name",
            render: (job: JobInfo) => job.name || job.id
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
            key: "queued_time",
            header: "Queued",
            render: (job: JobInfo) =>
                formatRelativeTime(job.queued_time)
        }
    ];

    return (
        <div className="dashboard">
            <ContentHeader
                title="Dashboard"
                description="Overview of your Colony Print infrastructure"
            />
            <div className="dashboard-stats">
                <StatCard
                    label="Nodes"
                    value={loading ? "-" : nodeCount}
                    description="Registered print nodes"
                />
                <StatCard
                    label="Jobs"
                    value={loading ? "-" : jobCount}
                    description="Total tracked jobs"
                />
                <StatCard
                    label="System Health"
                    value={
                        loading
                            ? "-"
                            : healthy
                              ? "Healthy"
                              : "Unreachable"
                    }
                    description="API server status"
                />
            </div>
            <div className="dashboard-recent">
                <DataTable
                    columns={columns}
                    data={recentJobs}
                    loading={loading}
                    emptyMessage="No recent jobs"
                />
            </div>
        </div>
    );
};
