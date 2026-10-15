import React, { FC, Fragment, useMemo } from "react";
import { useLocation } from "react-router-dom";
import {
    chevronForwardOutline,
    menuOutline,
    refreshOutline
} from "ionicons/icons";

import { Icon, Link } from "../atoms";
import { getBreadcrumbs } from "../../utils";
import { QuickSearch } from "./quick-search";

import "./top-bar.css";

interface TopBarProps {
    onToggleSidebar?: () => void;
    onRefresh?: () => void;
}

export const TopBar: FC<TopBarProps> = ({
    onToggleSidebar,
    onRefresh
}) => {
    const location = useLocation();
    const breadcrumbs = useMemo(
        () => getBreadcrumbs(location.pathname),
        [location.pathname]
    );
    return (
        <header className="top-bar">
            <div className="top-bar-left">
                {onToggleSidebar && (
                    <button
                        className="top-bar-toggle"
                        onClick={onToggleSidebar}
                        aria-label="Toggle menu"
                    >
                        <Icon icon={menuOutline} size="lg" />
                    </button>
                )}
                <nav className="top-bar-breadcrumb" aria-label="Breadcrumb">
                    <span className="top-bar-breadcrumb-root">
                        Colony Print
                    </span>
                    {breadcrumbs.map((breadcrumb, index) => (
                        <Fragment key={breadcrumb.path}>
                            <Icon icon={chevronForwardOutline} size="sm" />
                            {index < breadcrumbs.length - 1 ? (
                                <Link
                                    to={breadcrumb.path}
                                    style={["top-bar-breadcrumb-link"]}
                                >
                                    {breadcrumb.label}
                                </Link>
                            ) : (
                                <span
                                    className="top-bar-breadcrumb-current"
                                    aria-current="page"
                                >
                                    {breadcrumb.label}
                                </span>
                            )}
                        </Fragment>
                    ))}
                </nav>
            </div>
            <div className="top-bar-actions">
                <QuickSearch />
                {onRefresh && (
                    <button
                        className="top-bar-refresh"
                        type="button"
                        onClick={onRefresh}
                        aria-label="Refresh"
                        title="Refresh"
                    >
                        <Icon icon={refreshOutline} />
                    </button>
                )}
            </div>
        </header>
    );
};
