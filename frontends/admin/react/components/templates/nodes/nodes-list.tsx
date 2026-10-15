import React, { FC, useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { logoTux, logoWindows } from "ionicons/icons";

import { useAPI } from "../../../hooks";
import { NodeInfo } from "../../../api/colony-print";
import { Icon, Link, Status, Tag } from "../../atoms";
import { ContentHeader, DataTable, FilterTabs } from "../../molecules";
import {
    formatRelativeTime,
    formatTimestamp,
    isNodeBehind,
    isNodeOnline
} from "../../../utils";

import "./nodes-list.css";

interface NodeEntry {
    id: string;
    node: NodeInfo;
    jobs: number;
}

type StateFilter = "all" | "online" | "offline";

const STATE_FILTERS: StateFilter[] = ["all", "online", "offline"];

/**
 * The icons of the platforms of the nodes, by the name of their
 * operating system (as reported by Python's os.name).
 */
const PLATFORM_ICONS = new Map([
    ["nt", logoWindows],
    ["posix", logoTux]
]);

export const NodesList: FC = () => {
    const api = useAPI();
    const [params, setParams] = useSearchParams();
    const [entries, setEntries] = useState<NodeEntry[]>([]);
    const [version, setVersion] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);

    // the filter is kept in the address of the page, so that it's
    // kept on its refresh and can be linked to
    const state = params.get("state") as StateFilter;
    const filter = STATE_FILTERS.includes(state) ? state : "all";
    const setFilter = (value: StateFilter) =>
        setParams(value === "all" ? {} : { state: value }, { replace: true });

    const fetchNodes = useCallback(async () => {
        setLoading(true);
        try {
            const [data, info, jobs] = await Promise.all([
                api.listNodes(),
                api.getInfo().catch(() => null),
                api.listJobs().catch(() => ({}))
            ]);
            const jobValues = Object.values(jobs).filter((j) => j && j.id);
            const items = Object.entries(data)
                .filter(([, node]) => node && node.name)
                .map(([id, node]) => ({
                    id,
                    node,
                    jobs: jobValues.filter((job) => job.node_id === id)
                        .length
                }));
            setEntries(items);
            setVersion(info?.version ?? null);
        } catch {
            setEntries([]);
        } finally {
            setLoading(false);
        }
    }, [api]);

    useEffect(() => {
        fetchNodes();
    }, [fetchNodes]);

    const onlineCount = useMemo(
        () => entries.filter((entry) => isNodeOnline(entry.node)).length,
        [entries]
    );

    const filteredEntries = useMemo(
        () =>
            filter === "all"
                ? entries
                : entries.filter(
                      (entry) =>
                          isNodeOnline(entry.node) === (filter === "online")
                  ),
        [entries, filter]
    );

    const columns = [
        {
            key: "state",
            header: "State",
            render: (entry: NodeEntry) => (
                <Status
                    variant={isNodeOnline(entry.node) ? "success" : "default"}
                >
                    {isNodeOnline(entry.node) ? "Online" : "Offline"}
                </Status>
            )
        },
        {
            key: "node",
            header: "Node",
            render: (entry: NodeEntry) => (
                <Link to={`/nodes/${entry.id}`} style={["nodes-list-node"]}>
                    <span className="nodes-list-name">{entry.node.name}</span>{" "}
                    <span className="nodes-list-id">{entry.id}</span>
                </Link>
            )
        },
        {
            key: "location",
            header: "Location",
            render: (entry: NodeEntry) => (
                <span className="nodes-list-muted">
                    {entry.node.location || "-"}
                </span>
            )
        },
        {
            key: "mode",
            header: "Mode",
            render: (entry: NodeEntry) => (
                <Tag
                    variant={
                        entry.node.mode === "email"
                            ? "warning"
                            : "default"
                    }
                >
                    {entry.node.mode}
                </Tag>
            )
        },
        {
            key: "printer",
            header: "Printer",
            render: (entry: NodeEntry) => entry.node.printer || "-"
        },
        {
            key: "platform",
            header: "Platform",
            render: (entry: NodeEntry) => {
                const icon = PLATFORM_ICONS.get(entry.node.os);
                return (
                    <span className="nodes-list-platform">
                        {icon && <Icon icon={icon} size="sm" />}
                        {entry.node.platform || "-"}
                    </span>
                );
            }
        },
        {
            key: "engines",
            header: "Engines",
            render: (entry: NodeEntry) => (
                <span className="nodes-list-mono">
                    {(entry.node.engines || []).join(", ") || "-"}
                </span>
            )
        },
        {
            key: "version",
            header: "Version",
            render: (entry: NodeEntry) =>
                isNodeBehind(entry.node, version) ? (
                    <span
                        className="nodes-list-mono nodes-list-behind"
                        title={`Behind the server (${version})`}
                    >
                        {entry.node.version}
                    </span>
                ) : (
                    <span className="nodes-list-mono">
                        {entry.node.version || "-"}
                    </span>
                )
        },
        {
            key: "jobs",
            header: "Jobs",
            render: (entry: NodeEntry) => (
                <span className="nodes-list-mono">{entry.jobs}</span>
            )
        },
        {
            key: "last_ping",
            header: "Last Seen",
            render: (entry: NodeEntry) => (
                <span
                    className={
                        isNodeOnline(entry.node)
                            ? "nodes-list-mono"
                            : "nodes-list-mono nodes-list-behind"
                    }
                    title={formatTimestamp(entry.node.last_ping)}
                >
                    {formatRelativeTime(entry.node.last_ping)}
                </span>
            )
        }
    ];

    return (
        <div className="nodes-list">
            <ContentHeader
                title="Nodes"
                description="Registered print nodes, online when seen in the last 15 minutes"
                actions={
                    <FilterTabs
                        label="Filter by state"
                        value={filter}
                        onChange={setFilter}
                        tabs={[
                            {
                                value: "all",
                                label: "All",
                                count: entries.length
                            },
                            {
                                value: "online",
                                label: "Online",
                                count: onlineCount
                            },
                            {
                                value: "offline",
                                label: "Offline",
                                count: entries.length - onlineCount
                            }
                        ]}
                    />
                }
            />
            <DataTable
                columns={columns}
                data={filteredEntries}
                loading={loading}
                emptyMessage="No nodes registered"
                footer={
                    <>
                        <span className="nodes-list-footer">
                            {filteredEntries.length} of {entries.length} nodes
                        </span>
                        {version && (
                            <span className="nodes-list-legend">
                                <span className="nodes-list-swatch" />
                                Version behind the server ({version})
                            </span>
                        )}
                    </>
                }
            />
        </div>
    );
};
