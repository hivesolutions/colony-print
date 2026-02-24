import React, { ReactNode } from "react";

import { Card, Loader } from "../atoms";

import "./detail-grid.css";

interface DetailField {
    label: string;
    value: ReactNode;
}

interface DetailGridProps {
    fields: DetailField[];
    loading?: boolean;
}

export function DetailGrid({
    fields,
    loading = false
}: DetailGridProps) {
    if (loading) {
        return (
            <Card style={["detail-grid-loading"]}>
                <Loader />
            </Card>
        );
    }
    return (
        <Card style={["detail-grid-card"]}>
            <dl className="detail-grid">
                {fields.map((field, index) => (
                    <div key={index} className="detail-grid-row">
                        <dt className="detail-grid-label">
                            {field.label}
                        </dt>
                        <dd className="detail-grid-value">
                            {field.value}
                        </dd>
                    </div>
                ))}
            </dl>
        </Card>
    );
}
