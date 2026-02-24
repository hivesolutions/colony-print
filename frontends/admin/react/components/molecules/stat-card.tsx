import React, { FC } from "react";

import { Card, Title, Text } from "../atoms";

import "./stat-card.css";

interface StatCardProps {
    label: string;
    value: string | number;
    description?: string;
}

export const StatCard: FC<StatCardProps> = ({
    label,
    value,
    description
}) => {
    return (
        <Card style={["stat-card"]}>
            <Text variant="secondary">{label}</Text>
            <Title level={2} style={["stat-card-value"]}>
                {value}
            </Title>
            {description && (
                <Text variant="small">{description}</Text>
            )}
        </Card>
    );
};
