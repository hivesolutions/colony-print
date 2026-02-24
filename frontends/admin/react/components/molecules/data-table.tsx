import React, { ReactNode } from "react";

import { Card, Loader } from "../atoms";

import "./data-table.css";

interface Column<T> {
    key: string;
    header: string;
    render: (item: T) => ReactNode;
}

interface DataTableProps<T> {
    columns: Column<T>[];
    data: T[];
    loading?: boolean;
    emptyMessage?: string;
}

export function DataTable<T>({
    columns,
    data,
    loading = false,
    emptyMessage = "No data available"
}: DataTableProps<T>) {
    if (loading) {
        return (
            <Card style={["data-table-loading"]}>
                <Loader />
            </Card>
        );
    }
    return (
        <Card style={["data-table-card"]}>
            <table className="data-table">
                <thead>
                    <tr>
                        {columns.map((col) => (
                            <th key={col.key}>{col.header}</th>
                        ))}
                    </tr>
                </thead>
                <tbody>
                    {data.length === 0 ? (
                        <tr>
                            <td
                                colSpan={columns.length}
                                className="data-table-empty"
                            >
                                {emptyMessage}
                            </td>
                        </tr>
                    ) : (
                        data.map((item, index) => (
                            <tr key={index}>
                                {columns.map((col) => (
                                    <td key={col.key}>
                                        {col.render(item)}
                                    </td>
                                ))}
                            </tr>
                        ))
                    )}
                </tbody>
            </table>
        </Card>
    );
}
