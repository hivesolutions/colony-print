import React, { FC, useCallback, useEffect, useState } from "react";

import { useAPI } from "../../../hooks";
import { PrinterInfo } from "../../../api/colony-print";
import { Tag, Text } from "../../atoms";
import { ContentHeader, DataTable } from "../../molecules";

import "./printers-list.css";

export const PrintersList: FC = () => {
    const api = useAPI();
    const [printers, setPrinters] = useState<PrinterInfo[]>([]);
    const [loading, setLoading] = useState(true);

    const fetchPrinters = useCallback(async () => {
        setLoading(true);
        try {
            const data = await api.listPrinters();
            setPrinters(data);
        } catch {
            setPrinters([]);
        } finally {
            setLoading(false);
        }
    }, [api]);

    useEffect(() => {
        fetchPrinters();
    }, [fetchPrinters]);

    const columns = [
        {
            key: "name",
            header: "Name",
            render: (printer: PrinterInfo) => printer.name
        },
        {
            key: "is_default",
            header: "Default",
            render: (printer: PrinterInfo) =>
                printer.is_default ? (
                    <Tag variant="success">Yes</Tag>
                ) : (
                    <Text variant="secondary">No</Text>
                )
        },
        {
            key: "media",
            header: "Media",
            render: (printer: PrinterInfo) => printer.media || "-"
        },
        {
            key: "width",
            header: "Width",
            render: (printer: PrinterInfo) =>
                printer.width ? String(printer.width) : "-"
        },
        {
            key: "length",
            header: "Length",
            render: (printer: PrinterInfo) =>
                printer.length ? String(printer.length) : "-"
        }
    ];

    return (
        <div className="printers-list">
            <ContentHeader
                title="Printers"
                description="Available printers on the system"
            />
            <DataTable
                columns={columns}
                data={printers}
                loading={loading}
                emptyMessage="No printers available"
            />
        </div>
    );
};
