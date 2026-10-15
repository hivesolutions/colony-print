import React, {
    FC,
    ReactNode,
    useCallback,
    useContext,
    useEffect,
    useMemo,
    useRef,
    useState
} from "react";
import { useLocation } from "react-router-dom";
import {
    documentTextOutline,
    gridOutline,
    logOutOutline,
    printOutline,
    serverOutline,
    settingsOutline
} from "ionicons/icons";

import { useAPI, useLogout } from "../../hooks";
import { JobInfo, NodeInfo, ServerInfo } from "../../api/colony-print";
import { DataContext } from "../../contexts";
import { Icon, Link, Logo } from "../atoms";
import { countJobs, formatDuration, isNodeOnline } from "../../utils";
import { ConfirmDialog } from "./confirm-dialog";

import "./side-bar.css";

interface SideBarItem {
    label: string;
    path: string;
    icon: string;
}

interface SideBarGroup {
    label: string;
    items: SideBarItem[];
}

interface SideBarProps {
    open?: boolean;
    onClose?: () => void;
}

const GROUPS: SideBarGroup[] = [
    {
        label: "Monitor",
        items: [
            { label: "Dashboard", path: "/", icon: gridOutline },
            { label: "Nodes", path: "/nodes", icon: serverOutline },
            { label: "Jobs", path: "/jobs", icon: documentTextOutline },
            { label: "Printers", path: "/printers", icon: printOutline }
        ]
    },
    {
        label: "System",
        items: [
            { label: "Settings", path: "/settings", icon: settingsOutline }
        ]
    }
];

export const SideBar: FC<SideBarProps> = ({ open, onClose }) => {
    const api = useAPI();
    const location = useLocation();
    const { username } = useContext(DataContext);
    const [healthy, setHealthy] = useState<boolean | null>(null);
    const [info, setInfo] = useState<ServerInfo | null>(null);
    const [nodes, setNodes] = useState<NodeInfo[] | null>(null);
    const [jobs, setJobs] = useState<JobInfo[] | null>(null);

    // keeps the number of the navigation whose status is retrieved, so
    // that the status of a navigation (or of a side bar) that is gone
    // is ignored once retrieved, instead of replacing the current one
    const navigation = useRef(0);

    // the health of the API is the one of its (public) ping, its
    // version and uptime require the session, so that an expired
    // session is not shown as an unreachable server
    const fetchStatus = useCallback(async () => {
        const current = navigation.current;
        const [pingData, infoData, nodesData, jobsData] = await Promise.all([
            api.ping().catch(() => null),
            api.getInfo().catch(() => null),
            api.listNodes().catch(() => null),
            api.listJobs().catch(() => null)
        ]);
        if (navigation.current !== current) return;
        setHealthy(pingData !== null);
        setInfo(infoData);
        setNodes(
            nodesData
                ? Object.values(nodesData).filter((n) => n && n.name)
                : null
        );
        setJobs(
            jobsData ? Object.values(jobsData).filter((j) => j && j.id) : null
        );
    }, [api]);

    // refreshes the status on every navigation, so that the counts
    // of the nodes and jobs follow the ones shown in the pages
    useEffect(() => {
        fetchStatus();
        return () => {
            navigation.current++;
        };
    }, [fetchStatus, location.pathname]);

    const badges = useMemo(() => {
        const badges = new Map<string, ReactNode>();
        if (nodes) {
            const online = nodes.filter((node) => isNodeOnline(node)).length;
            badges.set(
                "/nodes",
                <span
                    className="side-bar-count"
                    title={`${online} of ${nodes.length} nodes online`}
                >
                    {online}/{nodes.length}
                </span>
            );
        }
        if (jobs) {
            const counts = countJobs(jobs);
            const inFlight = counts.printing + counts.queued;
            if (inFlight > 0) {
                badges.set(
                    "/jobs",
                    <span
                        className="side-bar-badge"
                        title={`${inFlight} jobs in flight`}
                    >
                        {inFlight}
                    </span>
                );
            }
        }
        return badges;
    }, [nodes, jobs]);

    const classes = useMemo(
        () =>
            ["side-bar", open ? "side-bar-open" : ""]
                .filter(Boolean)
                .join(" "),
        [open]
    );
    const session = [username, info && `server ${info.version}`]
        .filter(Boolean)
        .join(" · ");

    return (
        <nav className={classes} aria-label="Main">
            <div className="side-bar-brand">
                <Logo sliced={false} height={25} />
                {session && (
                    <span className="side-bar-session">{session}</span>
                )}
            </div>
            {GROUPS.map((group) => (
                <div key={group.label} className="side-bar-group">
                    <span className="side-bar-group-label">
                        {group.label}
                    </span>
                    <ul className="side-bar-list">
                        {group.items.map((item) => (
                            <SideBarLink
                                key={item.path}
                                item={item}
                                badge={badges.get(item.path)}
                                active={
                                    item.path === "/"
                                        ? location.pathname === "/"
                                        : location.pathname.startsWith(
                                              item.path
                                          )
                                }
                                onClick={onClose}
                            />
                        ))}
                    </ul>
                </div>
            ))}
            <SideBarFooter healthy={healthy} info={info} />
        </nav>
    );
};

const SideBarLink: FC<{
    item: SideBarItem;
    active: boolean;
    badge?: ReactNode;
    onClick?: () => void;
}> = ({ item, active, badge, onClick }) => {
    const classes = useMemo(
        () =>
            ["side-bar-link", active ? "side-bar-link-active" : ""]
                .filter(Boolean)
                .join(" "),
        [active]
    );
    return (
        <li>
            <Link
                to={item.path}
                style={[classes]}
                onClick={onClick}
                aria-current={active ? "page" : undefined}
            >
                <Icon icon={item.icon} />
                {item.label}
                {badge}
            </Link>
        </li>
    );
};

const SideBarFooter: FC<{
    healthy: boolean | null;
    info: ServerInfo | null;
}> = ({ healthy, info }) => {
    const logout = useLogout();
    const { username } = useContext(DataContext);
    const [confirming, setConfirming] = useState(false);

    const status =
        healthy === null
            ? "loading"
            : healthy
              ? "healthy"
              : "unreachable";

    return (
        <div className="side-bar-footer">
            <div className="side-bar-status">
                <span className="side-bar-status-label">
                    <span
                        className={`side-bar-status-dot side-bar-status-${status}`}
                    />
                    {healthy === null
                        ? "Connecting"
                        : healthy
                          ? "API healthy"
                          : "API unreachable"}
                </span>
                {info?.uptime !== null && info?.uptime !== undefined && (
                    <span className="side-bar-status-uptime">
                        up {formatDuration(info.uptime)}
                    </span>
                )}
            </div>
            {username && (
                <div className="side-bar-user">
                    <span className="side-bar-avatar" aria-hidden="true">
                        {username.slice(0, 2).toUpperCase()}
                    </span>
                    <span className="side-bar-user-name">{username}</span>
                    <button
                        className="side-bar-logout"
                        type="button"
                        onClick={() => setConfirming(true)}
                        aria-label="Log out"
                    >
                        <Icon icon={logOutOutline} />
                    </button>
                </div>
            )}
            {confirming && (
                <ConfirmDialog
                    title="Log out of Colony Print?"
                    message={`You're signed in as ${username}. You'll need to sign in again to manage the nodes, jobs and printers.`}
                    confirmLabel="Log out"
                    icon={logOutOutline}
                    onConfirm={logout}
                    onCancel={() => setConfirming(false)}
                />
            )}
        </div>
    );
};
