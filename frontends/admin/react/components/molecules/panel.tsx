import React, { FC, ReactNode } from "react";

import { Card, Icon, Title } from "../atoms";

import "./panel.css";

interface PanelHeaderProps {
    title: string;
    icon?: string;
    actions?: ReactNode;
}

interface PanelProps extends PanelHeaderProps {
    children?: ReactNode;
    style?: string[];
}

export const PanelHeader: FC<PanelHeaderProps> = ({
    title,
    icon,
    actions
}) => {
    return (
        <div className="panel-header">
            <Title level={3} style={["panel-title"]}>
                {icon && <Icon icon={icon} size="sm" />}
                {title}
            </Title>
            {actions && <div className="panel-actions">{actions}</div>}
        </div>
    );
};

export const Panel: FC<PanelProps> = ({
    title,
    icon,
    actions,
    children,
    style = []
}) => {
    return (
        <Card style={["panel", ...style]}>
            <PanelHeader title={title} icon={icon} actions={actions} />
            {children}
        </Card>
    );
};
