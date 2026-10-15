import React, { FC, useCallback, useEffect, useState } from "react";
import {
    chevronForwardOutline,
    documentTextOutline,
    pulseOutline,
    serverOutline,
    timeOutline
} from "ionicons/icons";

import { useAPI } from "../../../hooks";
import { NodeInfo, JobInfo, ServerInfo } from "../../../api/colony-print";
import { Icon, Link, Loader, Status, Tag } from "../../atoms";
import {
    ContentHeader,
    DataTable,
    DistributionBar,
    Panel,
    PanelHeader,
    StatCard
} from "../../molecules";
import {
    STATUS_VARIANTS,
    countJobs,
    formatDuration,
    formatRelativeTime,
    formatStatus,
    formatTime,
    formatTimestamp,
    isNodeBehind,
    isNodeOnline
} from "../../../utils";

import "./dashboard.css";

export const Dashboard: FC = () => {
    const api = useAPI();
    const [nodes, setNodes] = useState<Record<string, NodeInfo>>({});
    const [jobs, setJobs] = useState<Record<string, JobInfo>>({});
    const [healthy, setHealthy] = useState<boolean | null>(null);
    const [info, setInfo] = useState<ServerInfo | null>(null);
    const [updated, setUpdated] = useState<number | null>(null);
    const [loading, setLoading] = useState(true);

    const fetchData = useCallback(async () => {
        setLoading(true);
        try {
            const [nodesData, jobsData, pingData, infoData] =
                await Promise.all([
                    api.listNodes().catch(() => ({})),
                    api.listJobs().catch(() => ({})),
                    api.ping().catch(() => null),
                    api.getInfo().catch(() => null)
                ]);
            setNodes(nodesData);
            setJobs(jobsData);
            setHealthy(pingData !== null);
            setInfo(infoData);
            setUpdated(Date.now() / 1000);
        } finally {
            setLoading(false);
        }
    }, [api]);

    useEffect(() => {
        fetchData();
    }, [fetchData]);

    const nodeEntries = Object.entries(nodes)
        .filter(([, node]) => node && node.name)
        .map(([id, node]) => ({ id, node }));
    const nodeCount = nodeEntries.length;
    const onlineCount = nodeEntries.filter((entry) =>
        isNodeOnline(entry.node)
    ).length;
    const jobCount = Object.keys(jobs).length;
    const counts = countJobs(Object.values(jobs).filter((j) => j && j.id));
    const recentJobs = Object.values(jobs)
        .filter((j) => j && j.id)
        .sort((a, b) => (b.queued_time || 0) - (a.queued_time || 0))
        .slice(0, 10);

    const columns = [
        {
            key: "queued_time",
            header: "Queued",
            render: (job: JobInfo) => (
                <span
                    className="dashboard-time"
                    title={formatTimestamp(job.queued_time)}
                >
                    {formatRelativeTime(job.queued_time)}
                </span>
            )
        },
        {
            key: "name",
            header: "Job",
            render: (job: JobInfo) => (
                <Link to={`/jobs/${job.id}`} style={["dashboard-job"]}>
                    {job.name || job.id}
                </Link>
            )
        },
        {
            key: "node_id",
            header: "Node",
            render: (job: JobInfo) =>
                job.node_id ? (
                    <Link
                        to={`/nodes/${job.node_id}`}
                        style={["dashboard-mono"]}
                    >
                        {job.node_id}
                    </Link>
                ) : (
                    "-"
                )
        },
        {
            key: "status",
            header: "Status",
            render: (job: JobInfo) => (
                <Status variant={STATUS_VARIANTS.get(job.status)}>
                    {formatStatus(job.status)}
                </Status>
            )
        }
    ];

    const serverDetails = info
        ? [
              info.version,
              info.uptime !== null && info.uptime !== undefined
                  ? `up ${formatDuration(info.uptime)}`
                  : null
          ]
              .filter(Boolean)
              .join(", ")
        : null;

    return (
        <div className="dashboard">
            <ContentHeader
                title="Dashboard"
                description={
                    updated
                        ? `Overview of your Colony Print infrastructure, updated ${formatTime(updated)}`
                        : "Overview of your Colony Print infrastructure"
                }
            />
            <div className="dashboard-stats">
                <StatCard
                    label="Nodes"
                    icon={serverOutline}
                    value={loading ? "-" : nodeCount}
                    description={
                        loading ? (
                            "Registered print nodes"
                        ) : (
                            <>
                                <span
                                    className={
                                        onlineCount > 0
                                            ? "dashboard-success"
                                            : undefined
                                    }
                                >
                                    {onlineCount} online
                                </span>
                                , {nodeCount - onlineCount} offline
                            </>
                        )
                    }
                />
                <StatCard
                    label="Jobs Tracked"
                    icon={documentTextOutline}
                    value={loading ? "-" : jobCount}
                    description={
                        loading ? (
                            "Total tracked jobs"
                        ) : (
                            <>
                                {counts.succeeded} ok,{" "}
                                <span
                                    className={
                                        counts.failed > 0
                                            ? "dashboard-error"
                                            : undefined
                                    }
                                >
                                    {counts.failed} failed
                                </span>
                            </>
                        )
                    }
                />
                <StatCard
                    label="In Flight"
                    icon={timeOutline}
                    value={loading ? "-" : counts.printing + counts.queued}
                    description={`${counts.printing} printing, ${counts.queued} queued`}
                />
                <StatCard
                    label="API"
                    icon={pulseOutline}
                    value={
                        loading ? (
                            "-"
                        ) : (
                            <Status
                                variant={healthy ? "success" : "error"}
                                style={["dashboard-health"]}
                            >
                                {healthy ? "Healthy" : "Unreachable"}
                            </Status>
                        )
                    }
                    description={
                        serverDetails ? (
                            <span className="dashboard-mono">
                                {serverDetails}
                            </span>
                        ) : (
                            "API server status"
                        )
                    }
                />
            </div>
            <DistributionBar
                title="Jobs by Status"
                description={`The ${jobCount} jobs kept by the server`}
                items={[
                    {
                        label: "Succeeded",
                        count: counts.succeeded,
                        variant: "success"
                    },
                    {
                        label: "Failed",
                        count: counts.failed,
                        variant: "error"
                    },
                    {
                        label: "Printing",
                        count: counts.printing,
                        variant: "warning"
                    },
                    {
                        label: "Queued",
                        count: counts.queued,
                        variant: "info"
                    },
                    {
                        label: "Cancelled",
                        count: counts.cancelled,
                        variant: "default"
                    }
                ]}
            />
            <div className="dashboard-panels">
                <section className="dashboard-panel dashboard-panel-wide">
                    <DataTable
                        header={
                            <PanelHeader
                                title="Recent Jobs"
                                actions={
                                    <Link
                                        to="/jobs"
                                        style={["dashboard-more"]}
                                    >
                                        All jobs
                                        <Icon
                                            icon={chevronForwardOutline}
                                            size="sm"
                                        />
                                    </Link>
                                }
                            />
                        }
                        columns={columns}
                        data={recentJobs}
                        loading={loading}
                        emptyMessage="No recent jobs"
                    />
                </section>
                <section className="dashboard-panel">
                    <Panel
                        title="Node Status"
                        actions={
                            <Link to="/nodes" style={["dashboard-more"]}>
                                All nodes
                                <Icon icon={chevronForwardOutline} size="sm" />
                            </Link>
                        }
                    >
                        {loading ? (
                            <div className="dashboard-loading">
                                <Loader />
                            </div>
                        ) : nodeEntries.length === 0 ? (
                            <div className="dashboard-empty">
                                No nodes registered
                            </div>
                        ) : (
                            <ul className="dashboard-nodes">
                                {nodeEntries.map((entry) => (
                                    <li key={entry.id}>
                                        <Link
                                            to={`/nodes/${entry.id}`}
                                            style={["dashboard-node"]}
                                        >
                                            <Status
                                                variant={
                                                    isNodeOnline(entry.node)
                                                        ? "success"
                                                        : "default"
                                                }
                                                role="img"
                                                aria-label={
                                                    isNodeOnline(entry.node)
                                                        ? "Online"
                                                        : "Offline"
                                                }
                                            />
                                            <span className="dashboard-node-name">
                                                {entry.node.name}{" "}
                                                <span className="dashboard-node-id">
                                                    {entry.id}
                                                </span>
                                            </span>
                                            {isNodeBehind(
                                                entry.node,
                                                info?.version
                                            ) ? (
                                                <Tag variant="warning">
                                                    {entry.node.version}
                                                </Tag>
                                            ) : (
                                                <span className="dashboard-node-version">
                                                    {entry.node.version || "-"}
                                                </span>
                                            )}
                                            <span
                                                className={
                                                    isNodeOnline(entry.node)
                                                        ? "dashboard-node-seen"
                                                        : "dashboard-node-seen dashboard-node-offline"
                                                }
                                            >
                                                {formatRelativeTime(
                                                    entry.node.last_ping
                                                )}
                                            </span>
                                        </Link>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </Panel>
                </section>
            </div>
        </div>
    );
};
