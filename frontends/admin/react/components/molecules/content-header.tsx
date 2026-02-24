import React, { FC, ReactNode } from "react";

import { Title, Text } from "../atoms";

import "./content-header.css";

interface ContentHeaderProps {
    title: string;
    description?: string;
    actions?: ReactNode;
}

export const ContentHeader: FC<ContentHeaderProps> = ({
    title,
    description,
    actions
}) => {
    return (
        <div className="content-header">
            <div className="content-header-text">
                <Title level={1}>{title}</Title>
                {description && (
                    <Text variant="secondary">{description}</Text>
                )}
            </div>
            {actions && (
                <div className="content-header-actions">{actions}</div>
            )}
        </div>
    );
};
