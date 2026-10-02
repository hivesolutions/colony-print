import React, { FC } from "react";

import { Card, Title, Text } from "../atoms";

import "./stat-card.css";

interface StatCardProps {
    label: string;
    value: string | number;
    description?: string;
    style?: string[];
}

export const StatCard: FC<StatCardProps> = ({
    label,
    value,
    description,
    style = []
}) => {
    return (
        <Card style={["stat-card", ...style]}>
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
