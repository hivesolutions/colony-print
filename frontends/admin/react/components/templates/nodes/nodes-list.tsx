import React, { FC, useCallback, useEffect, useState } from "react";

import { useAPI } from "../../../hooks";
import { NodeInfo } from "../../../api/colony-print";
import { Link, Tag } from "../../atoms";
import { ContentHeader, DataTable } from "../../molecules";
import { formatRelativeTime } from "../../../utils";

import "./nodes-list.css";

interface NodeEntry {
    id: string;
    node: NodeInfo;
}

export const NodesList: FC = () => {
    const api = useAPI();
    const [entries, setEntries] = useState<NodeEntry[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchNodes = useCallback(async () => {
        setLoading(true);
        try {
            const data = await api.listNodes();
            const items = Object.entries(data)
                .filter(([, node]) => node && node.name)
                .map(([id, node]) => ({
                    id,
                    node
                }));
            setEntries(items);
        } catch {
            setEntries([]);
        } finally {
            setLoading(false);
        }
    }, [api]);

    useEffect(() => {
        fetchNodes();
    }, [fetchNodes]);

    const columns = [
        {
            key: "id",
            header: "ID",
            render: (entry: NodeEntry) => (
                <Link to={`/nodes/${entry.id}`}>
                    {entry.id}
                </Link>
            )
        },
        {
            key: "name",
            header: "Name",
            render: (entry: NodeEntry) => entry.node.name
        },
        {
            key: "location",
            header: "Location",
            render: (entry: NodeEntry) => entry.node.location
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
            render: (entry: NodeEntry) => entry.node.printer
        },
        {
            key: "engines",
            header: "Engines",
            render: (entry: NodeEntry) =>
                (entry.node.engines || []).join(", ") || "-"
        },
        {
            key: "platform",
            header: "Platform",
            render: (entry: NodeEntry) => entry.node.platform || "-"
        },
        {
            key: "version",
            header: "Version",
            render: (entry: NodeEntry) => entry.node.version || "-"
        },
        {
            key: "last_ping",
            header: "Last Seen",
            render: (entry: NodeEntry) =>
                formatRelativeTime(entry.node.last_ping)
        }
    ];

    return (
        <div className="nodes-list">
            <ContentHeader
                title="Nodes"
                description="Registered print nodes in the infrastructure"
            />
            <DataTable
                columns={columns}
                data={entries}
                loading={loading}
                emptyMessage="No nodes registered"
            />
        </div>
    );
};
