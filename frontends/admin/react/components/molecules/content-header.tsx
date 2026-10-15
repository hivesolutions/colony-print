import React, { FC, ReactNode } from "react";

import { Title, Text } from "../atoms";

import "./content-header.css";

interface ContentHeaderProps {
    title: string;
    description?: string;
    meta?: ReactNode;
    actions?: ReactNode;
}

export const ContentHeader: FC<ContentHeaderProps> = ({
    title,
    description,
    meta,
    actions
}) => {
    return (
        <div className="content-header">
            <div className="content-header-text">
                <div className="content-header-title">
                    <Title level={1}>{title}</Title>
                    {meta}
                </div>
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
