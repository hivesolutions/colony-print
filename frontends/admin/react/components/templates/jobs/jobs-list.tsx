import React, { FC, useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import {
    cloudDownloadOutline,
    diamondOutline,
    documentTextOutline,
    printOutline,
    reloadOutline,
    searchOutline,
    syncOutline,
    textOutline
} from "ionicons/icons";

import { useAPI } from "../../../hooks";
import { JobInfo } from "../../../api/colony-print";
import { Icon, Link, Status, TextInput } from "../../atoms";
import { ContentHeader, DataTable, FilterTabs } from "../../molecules";
import {
    STATUS_VARIANTS,
    formatStatus,
    formatTime,
    formatTimestamp,
    formatVersions
} from "../../../utils";

import "./jobs-list.css";

type StatusFilter = "all" | "queued" | "printing" | "finished" | "cancelled";

const STATUS_FILTERS: StatusFilter[] = [
    "all",
    "queued",
    "printing",
    "finished",
    "cancelled"
];

/**
 * The icons of the types of the jobs, the engines that print
 * them and the commands for their nodes.
 */
const TYPE_ICONS = new Map([
    ["npcolony", printOutline],
    ["gravo", diamondOutline],
    ["text", documentTextOutline],
    ["fonts", textOutline],
    ["restart", reloadOutline],
    ["update", cloudDownloadOutline],
    ["auto-update", syncOutline]
]);

export const JobsList: FC = () => {
    const api = useAPI();
    const [params, setParams] = useSearchParams();
    const [jobs, setJobs] = useState<JobInfo[]>([]);
    const [loading, setLoading] = useState(true);

    // the filters are kept in the address of the page, so that
    // they're kept on its refresh and can be linked to
    const status = params.get("status") as StatusFilter;
    const filter = STATUS_FILTERS.includes(status) ? status : "all";
    const query = params.get("query") || "";
    const setFilters = (filter: StatusFilter, query: string) =>
        setParams(
            {
                ...(filter === "all" ? {} : { status: filter }),
                ...(query ? { query: query } : {})
            },
            { replace: true }
        );

    const fetchJobs = useCallback(async () => {
        setLoading(true);
        try {
            const data = await api.listJobs();
            const items = Object.values(data)
                .filter((j) => j && j.id)
                .sort(
                    (a, b) =>
                        (b.queued_time || 0) - (a.queued_time || 0)
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

    const filteredJobs = useMemo(() => {
        const value = query.trim().toLowerCase();
        return jobs
            .filter((j) => filter === "all" || j.status === filter)
            .filter(
                (j) =>
                    !value ||
                    j.id.toLowerCase().startsWith(value) ||
                    [j.name, j.node_id].some((field) =>
                        (field || "").toLowerCase().includes(value)
                    )
            );
    }, [jobs, filter, query]);

    const columns = [
        {
            key: "queued_time",
            header: "Queued",
            render: (job: JobInfo) => (
                <span
                    className="jobs-list-time"
                    title={formatTimestamp(job.queued_time)}
                >
                    {formatTime(job.queued_time)}
                </span>
            )
        },
        {
            key: "id",
            header: "ID",
            render: (job: JobInfo) => (
                <Link to={`/jobs/${job.id}`} style={["jobs-list-id"]}>
                    {job.id.substring(0, 8)}
                </Link>
            )
        },
        {
            key: "name",
            header: "Name",
            render: (job: JobInfo) => (
                <span className="jobs-list-name">{job.name || "-"}</span>
            )
        },
        {
            key: "node_id",
            header: "Node",
            render: (job: JobInfo) =>
                job.node_id ? (
                    <Link
                        to={`/nodes/${job.node_id}`}
                        style={["jobs-list-node"]}
                    >
                        {job.node_id}
                    </Link>
                ) : (
                    "-"
                )
        },
        {
            key: "type",
            header: "Type",
            render: (job: JobInfo) => {
                if (!job.type) return "-";
                const icon = TYPE_ICONS.get(job.type);
                return (
                    <span className="jobs-list-type">
                        {icon && <Icon icon={icon} size="sm" />}
                        {job.type}
                    </span>
                );
            }
        },
        {
            key: "format",
            header: "Format",
            render: (job: JobInfo) => (
                <span className="jobs-list-mono">{job.format || "-"}</span>
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
        },
        {
            key: "result",
            header: "Result",
            render: (job: JobInfo) => {
                const result = job.result?.result as
                    | string
                    | undefined;
                if (!result) {
                    return <span className="jobs-list-empty">-</span>;
                }
                return (
                    <span className="jobs-list-result">
                        <span className={`jobs-list-result-${result}`}>
                            {result}
                        </span>
                        {job.result?.before !== undefined && (
                            <span className="jobs-list-versions">
                                {formatVersions(job)}
                            </span>
                        )}
                    </span>
                );
            }
        },
        {
            key: "finish_time",
            header: "Finished",
            render: (job: JobInfo) => (
                <span
                    className="jobs-list-time"
                    title={formatTimestamp(job.finish_time)}
                >
                    {formatTime(job.finish_time)}
                </span>
            )
        }
    ];

    return (
        <div className="jobs-list">
            <ContentHeader
                title="Jobs"
                description="Print jobs across all nodes"
            />
            <DataTable
                header={
                    <div className="jobs-list-filters">
                        <FilterTabs
                            label="Filter by status"
                            variant="underline"
                            value={filter}
                            onChange={(value) => setFilters(value, query)}
                            tabs={STATUS_FILTERS.map((f) => ({
                                value: f,
                                label: f === "all" ? "All" : formatStatus(f),
                                count:
                                    f === "all"
                                        ? jobs.length
                                        : jobs.filter((j) => j.status === f)
                                              .length
                            }))}
                        />
                        <span className="jobs-list-search">
                            <Icon icon={searchOutline} size="sm" />
                            <TextInput
                                type="search"
                                aria-label="Filter jobs"
                                placeholder="Filter by name, node or ID"
                                value={query}
                                onChange={(e) =>
                                    setFilters(filter, e.target.value)
                                }
                                style={["jobs-list-query"]}
                            />
                        </span>
                    </div>
                }
                columns={columns}
                data={filteredJobs}
                loading={loading}
                emptyMessage="No jobs found"
                footer={
                    <span className="jobs-list-footer">
                        {filteredJobs.length} of {jobs.length} jobs
                    </span>
                }
            />
        </div>
    );
};
