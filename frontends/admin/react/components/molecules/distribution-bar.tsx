import React, { FC } from "react";

import { Card, Text, Title } from "../atoms";

import "./distribution-bar.css";

interface DistributionItem {
    label: string;
    count: number;
    variant: "success" | "error" | "warning" | "info" | "default";
}

interface DistributionBarProps {
    title: string;
    description?: string;
    items: DistributionItem[];
}

export const DistributionBar: FC<DistributionBarProps> = ({
    title,
    description,
    items
}) => {
    return (
        <Card style={["distribution-bar"]}>
            <div className="distribution-bar-header">
                <Title level={3}>{title}</Title>
                {description && (
                    <Text
                        variant="small"
                        style={["distribution-bar-description"]}
                    >
                        {description}
                    </Text>
                )}
            </div>
            <div className="distribution-bar-track" aria-hidden="true">
                {items
                    .filter((item) => item.count > 0)
                    .map((item) => (
                        <span
                            key={item.label}
                            className={`distribution-bar-segment distribution-bar-${item.variant}`}
                            style={{ flexGrow: item.count }}
                        />
                    ))}
            </div>
            <ul className="distribution-bar-legend">
                {items.map((item) => (
                    <li key={item.label} className="distribution-bar-item">
                        <span
                            className={`distribution-bar-swatch distribution-bar-${item.variant}`}
                        />
                        {item.label}
                        <span className="distribution-bar-count">
                            {item.count}
                        </span>
                    </li>
                ))}
            </ul>
        </Card>
    );
};
