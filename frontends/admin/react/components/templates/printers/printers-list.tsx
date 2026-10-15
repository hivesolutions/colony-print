import React, { FC, useCallback, useEffect, useState } from "react";
import { printOutline } from "ionicons/icons";

import { useAPI } from "../../../hooks";
import { NodePrinterInfo, PrinterInfo } from "../../../api/colony-print";
import { Button, Icon, Link, Status, Tag } from "../../atoms";
import { ContentHeader, DataTable, PanelHeader } from "../../molecules";
import { formatPaper, isNodeDefault, isNodeOnline } from "../../../utils";

import "./printers-list.css";

interface PrinterEntry {
    key: string;
    printer: NodePrinterInfo;
    online: boolean;
}

type TestState = "pending" | "queued" | "failed";

export const PrintersList: FC = () => {
    const api = useAPI();
    const [entries, setEntries] = useState<PrinterEntry[]>([]);
    const [printers, setPrinters] = useState<PrinterInfo[]>([]);
    const [tests, setTests] = useState<Record<string, TestState>>({});
    const [loading, setLoading] = useState(true);

    const fetchPrinters = useCallback(async () => {
        setLoading(true);
        try {
            const [nodesData, data] = await Promise.all([
                api.listNodePrinters().catch(() => []),
                api.listPrinters().catch(() => [])
            ]);

            // the state of the nodes is taken once (as they're retrieved),
            // so that the rows and the footer agree on it
            setEntries(
                nodesData.map((printer) => ({
                    key: `${printer.node_id}/${printer.name}`,
                    printer,
                    online: isNodeOnline(printer)
                }))
            );
            setPrinters(data);
        } finally {
            setLoading(false);
        }
    }, [api]);

    useEffect(() => {
        fetchPrinters();
    }, [fetchPrinters]);

    const printTest = async (entry: PrinterEntry) => {
        setTests((prev) => ({ ...prev, [entry.key]: "pending" }));
        try {
            await api.printNodeHello(entry.printer.node_id, entry.printer.name);
            setTests((prev) => ({ ...prev, [entry.key]: "queued" }));
        } catch {
            setTests((prev) => ({ ...prev, [entry.key]: "failed" }));
        }
    };

    const nodeIds = new Set(entries.map((entry) => entry.printer.node_id));
    const offlineIds = new Set(
        entries
            .filter((entry) => !entry.online)
            .map((entry) => entry.printer.node_id)
    );

    const columns = [
        {
            key: "name",
            header: "Printer",
            render: (entry: PrinterEntry) => (
                <span className="printers-list-name">
                    <span className="printers-list-strong">
                        {entry.printer.name}
                    </span>
                    {isNodeDefault(entry.printer) && <Tag>default</Tag>}
                </span>
            )
        },
        {
            key: "node",
            header: "Node",
            render: (entry: PrinterEntry) => (
                <Link
                    to={`/nodes/${encodeURIComponent(entry.printer.node_id)}`}
                    style={["printers-list-node"]}
                >
                    <Status
                        variant={entry.online ? "success" : "default"}
                        role="img"
                        aria-label={entry.online ? "Online" : "Offline"}
                    />{" "}
                    <span>
                        {entry.printer.node_name || entry.printer.node_id}
                    </span>{" "}
                    <span className="printers-list-mono">
                        {entry.printer.node_id}
                    </span>
                </Link>
            )
        },
        {
            key: "engine",
            header: "Engine",
            render: (entry: PrinterEntry) => (
                <span className="printers-list-mono">
                    {entry.printer.engine}
                </span>
            )
        },
        {
            key: "media",
            header: "Media",
            render: (entry: PrinterEntry) => (
                <span className="printers-list-mono">
                    {entry.printer.media || "-"}
                </span>
            )
        },
        {
            key: "paper",
            header: "Paper",
            render: (entry: PrinterEntry) => (
                <PaperSize
                    width={entry.printer.width}
                    length={entry.printer.length}
                />
            )
        },
        {
            key: "test",
            header: "Test",
            render: (entry: PrinterEntry) => {
                // the test page is a document printed by npcolony, which
                // is queued until the node is seen again when offline
                if (entry.printer.engine !== "npcolony") {
                    return (
                        <span
                            className="printers-list-none"
                            title={`Test pages are printed by npcolony, not by ${entry.printer.engine}`}
                        >
                            No test page
                        </span>
                    );
                }
                if (!entry.online) {
                    return (
                        <span
                            className="printers-list-none"
                            title="The node is offline, its test page would wait for it"
                        >
                            Node offline
                        </span>
                    );
                }
                if (tests[entry.key] === "queued") {
                    return <Status variant="info">Test page queued</Status>;
                }
                return (
                    <span className="printers-list-test">
                        {tests[entry.key] === "failed" && (
                            <Status variant="error">Failed</Status>
                        )}
                        <Button
                            variant="secondary"
                            size="sm"
                            disabled={tests[entry.key] === "pending"}
                            onClick={() => printTest(entry)}
                            style={["printers-list-button"]}
                        >
                            <Icon icon={printOutline} size="sm" />
                            Test page
                        </Button>
                    </span>
                );
            }
        }
    ];

    const serverColumns = [
        {
            key: "name",
            header: "Printer",
            render: (printer: PrinterInfo) => (
                <span className="printers-list-name">
                    <span className="printers-list-strong">{printer.name}</span>
                    {printer.is_default && <Tag>default</Tag>}
                </span>
            )
        },
        {
            key: "media",
            header: "Media",
            render: (printer: PrinterInfo) => (
                <span className="printers-list-mono">
                    {printer.media || "-"}
                </span>
            )
        },
        {
            key: "paper",
            header: "Paper",
            render: (printer: PrinterInfo) => (
                <PaperSize width={printer.width} length={printer.length} />
            )
        }
    ];

    return (
        <div className="printers-list">
            <ContentHeader
                title="Printers"
                description="The printers reported by every node, and the ones of the server"
            />
            <DataTable
                header={
                    <PanelHeader
                        title="Nodes"
                        actions={
                            <span className="printers-list-mono">
                                {entries.length}
                            </span>
                        }
                    />
                }
                columns={columns}
                data={entries}
                loading={loading}
                emptyMessage="No printers reported by the nodes"
                footer={
                    <span className="printers-list-footer">
                        {entries.length} printers on {nodeIds.size} nodes
                        {offlineIds.size > 0 &&
                            `, ${offlineIds.size} of them offline`}
                    </span>
                }
            />
            <DataTable
                header={
                    <PanelHeader
                        title="Server"
                        actions={
                            <span className="printers-list-mono">
                                {printers.length}
                            </span>
                        }
                    />
                }
                columns={serverColumns}
                data={printers}
                loading={loading}
                emptyMessage="No printers on the server"
            />
        </div>
    );
};

const PaperSize: FC<{ width?: number; length?: number }> = ({
    width,
    length
}) => (
    <span
        className="printers-list-mono"
        title={width && length ? `${width} × ${length} pt` : undefined}
    >
        {formatPaper(width, length)}
    </span>
);
