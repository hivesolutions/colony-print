import React, { FC, ReactNode } from "react";

import { Card, Icon, Title, Text } from "../atoms";

import "./stat-card.css";

interface StatCardProps {
    label: string;
    value: ReactNode;
    description?: ReactNode;
    icon?: string;
    style?: string[];
}

export const StatCard: FC<StatCardProps> = ({
    label,
    value,
    description,
    icon,
    style = []
}) => {
    return (
        <Card style={["stat-card", ...style]}>
            <Text variant="secondary" style={["stat-card-label"]}>
                {icon && <Icon icon={icon} size="sm" />}
                {label}
            </Text>
            <Title level={2} style={["stat-card-value"]}>
                {value}
            </Title>
            {description && (
                <Text variant="secondary" style={["stat-card-description"]}>
                    {description}
                </Text>
            )}
        </Card>
    );
};
