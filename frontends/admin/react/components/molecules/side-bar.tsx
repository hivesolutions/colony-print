import React, { FC, useMemo } from "react";
import { useLocation } from "react-router-dom";

import { Link } from "../atoms";

import "./side-bar.css";

interface SideBarItem {
    label: string;
    path: string;
}

const ITEMS: SideBarItem[] = [
    { label: "Dashboard", path: "/" },
    { label: "Nodes", path: "/nodes" },
    { label: "Jobs", path: "/jobs" },
    { label: "Printers", path: "/printers" },
    { label: "Settings", path: "/settings" }
];

export const SideBar: FC = () => {
    const location = useLocation();
    return (
        <nav className="side-bar">
            <ul className="side-bar-list">
                {ITEMS.map((item) => (
                    <SideBarLink
                        key={item.path}
                        item={item}
                        active={
                            item.path === "/"
                                ? location.pathname === "/"
                                : location.pathname.startsWith(item.path)
                        }
                    />
                ))}
            </ul>
        </nav>
    );
};

const SideBarLink: FC<{ item: SideBarItem; active: boolean }> = ({
    item,
    active
}) => {
    const classes = useMemo(
        () =>
            ["side-bar-link", active ? "side-bar-link-active" : ""]
                .filter(Boolean)
                .join(" "),
        [active]
    );
    return (
        <li>
            <Link to={item.path} style={[classes]}>
                {item.label}
            </Link>
        </li>
    );
};
