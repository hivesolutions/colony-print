import React, {
    FC,
    useCallback,
    useEffect,
    useRef,
    useState
} from "react";
import { useParams } from "react-router-dom";
import {
    arrowBackOutline,
    cloudDownloadOutline,
    pulseOutline,
    reloadOutline,
    syncOutline
} from "ionicons/icons";

import { useAPI } from "../../../hooks";
import {
    JobInfo,
    NodeInfo,
    NodeFontInfo
} from "../../../api/colony-print";
import { Button, Icon, Link, Status, Switch, Tag } from "../../atoms";
import {
    ContentHeader,
    DataTable,
    DetailGrid,
    Panel,
    PanelHeader,
    StatCard
} from "../../molecules";
import {
    formatRelativeTime,
    formatTimestamp,
    isNodeOnline,
    isRestartPending
} from "../../../utils";

import "./node-show.css";

export const NodeShow: FC = () => {
    const api = useAPI();
    const { id } = useParams<{ id: string }>();
    const [node, setNode] = useState<NodeInfo | null>(null);
    const [pending, setPending] = useState<JobInfo | null>(null);
    const [loading, setLoading] = useState(true);
    const [restarting, setRestarting] = useState(false);
    const [toggling, setToggling] = useState(false);

    // keeps the identifier of the node that is being shown, so that
    // the requests of another node (or of a view that is gone) are
    // ignored once they're done, instead of being shown as its own
    const shownId = useRef<string | undefined>(id);
    useEffect(() => {
        shownId.current = id;
        return () => {
            shownId.current = undefined;
        };
    }, [id]);

    const fetchNode = useCallback(
        async (silent = false) => {
            if (!id) return;
            if (!silent) setLoading(true);
            try {
                const data = await api.getNode(id);
                if (shownId.current !== id) return;
                setNode(data);
            } catch {
                if (shownId.current !== id) return;
                setNode(null);
            } finally {
                if (shownId.current === id) setLoading(false);
            }

            // retrieves the job (restart or update) that is going to
            // restart the node, if any, as the node doesn't get another
            // one while it's queued or in flight
            try {
                const jobs = await api.listJobs();
                if (shownId.current !== id) return;
                setPending(
                    Object.values(jobs).find(
                        (job) =>
                            job.node_id === id && isRestartPending(job)
                    ) || null
                );
            } catch {
                if (shownId.current !== id) return;
                setPending(null);
            }
        },
        [api, id]
    );

    useEffect(() => {
        fetchNode();
    }, [fetchNode]);

    // refreshes the node while its restart is pending, so that its
    // new start time and versions show up without a reload
    const pendingId = pending?.id;
    useEffect(() => {
        if (!pendingId) return;
        const interval = setInterval(() => fetchNode(true), 3000);
        return () => clearInterval(interval);
    }, [pendingId, fetchNode]);

    const restartNode = useCallback(
        async (update = false) => {
            if (!id) return;
            const message = update
                ? `Update the node ${id}? The node is restarted and updates its packages on the way up.`
                : `Restart the node ${id}? The node is restarted once its pending jobs are printed.`;
            if (!window.confirm(message)) return;
            setRestarting(true);
            try {
                if (update) await api.updateNode(id);
                else await api.restartNode(id);
            } catch {
                // ignores the error as the node refresh below will
                // reflect the actual (server-side) node state
            } finally {
                await fetchNode(true);
                setRestarting(false);
            }
        },
        [api, id, fetchNode]
    );

    const setAutoUpdate = useCallback(
        async (enabled: boolean) => {
            if (!id) return;
            setToggling(true);
            try {
                await api.setNodeAutoUpdate(id, enabled);

                // waits for the node to apply the change and to report
                // it, as it's sent to the node as any other job
                for (let index = 0; index < 10; index++) {
                    await new Promise((resolve) =>
                        setTimeout(resolve, 1000)
                    );
                    if (shownId.current !== id) break;
                    const data = await api.getNode(id);
                    if (shownId.current !== id) break;
                    setNode(data);
                    if (data.update?.auto === enabled) break;
                }
            } catch {
                // ignores the error as the node keeps showing its
                // actual (reported) auto-update state
            } finally {
                setToggling(false);
            }
        },
        [api, id]
    );

    const canRestart = node?.capabilities?.includes("restart");
    const canUpdate = node?.capabilities?.includes("update");
    const canAutoUpdate = node?.capabilities?.includes("auto-update");
    const online = isNodeOnline(node);

    const system = node?.system;

    const systemFields = system
        ? [
              {
                  label: "System",
                  value:
                      [system.name, system.release]
                          .filter(Boolean)
                          .join(" ") || "-"
              },
              ...(system.distribution
                  ? [
                        {
                            label: "Distribution",
                            value: system.distribution
                        }
                    ]
                  : []),
              {
                  label: "System Version",
                  value: system.version || "-"
              },
              {
                  label: "Architecture",
                  value:
                      [
                          system.machine,
                          system.architecture &&
                              `(${system.architecture})`
                      ]
                          .filter(Boolean)
                          .join(" ") || "-"
              }
          ]
        : [];

    const fields = node
        ? [
              { label: "Location", value: node.location || "-" },
              {
                  label: "Mode",
                  value: (
                      <Tag
                          variant={
                              node.mode === "email"
                                  ? "warning"
                                  : "default"
                          }
                      >
                          {node.mode}
                      </Tag>
                  )
              },
              { label: "Printer", value: node.printer || "-" },
              {
                  label: "Engines",
                  value: (
                      <span className="node-show-mono">
                          {(node.engines || []).join(", ") || "-"}
                      </span>
                  )
              },
              { label: "Platform", value: node.platform || "-" },
              { label: "OS", value: node.os || "-" },
              ...systemFields,
              {
                  label: "Version",
                  value: (
                      <span className="node-show-mono">
                          {node.version || "-"}
                      </span>
                  )
              },
              {
                  label: "Started",
                  value: node.start_time ? (
                      <>
                          {formatTimestamp(node.start_time)}{" "}
                          <span className="node-show-muted">
                              ({formatRelativeTime(node.start_time)})
                          </span>
                      </>
                  ) : (
                      "-"
                  )
              }
          ]
        : [];

    const engineEntries = node?.engine_info
        ? Object.entries(node.engine_info)
        : [];

    const libraryEntries = node?.libraries
        ? Object.entries(node.libraries)
        : [];

    const capabilities = node?.capabilities || [];

    const stats = node?.stats;
    const last = stats?.last;
    const update = node?.update;

    return (
        <div className="node-show">
            <ContentHeader
                title={node?.name || "Node"}
                meta={
                    <>
                        {id && <span className="node-show-id">{id}</span>}
                        {node && (
                            <span
                                className="node-show-state"
                                title={formatTimestamp(node.last_ping)}
                            >
                                <Status
                                    variant={online ? "success" : "default"}
                                >
                                    {online ? "Online" : "Offline"}
                                    {node.last_ping &&
                                        `, seen ${formatRelativeTime(node.last_ping)}`}
                                </Status>
                            </span>
                        )}
                    </>
                }
                actions={
                    <>
                        {pending ? (
                            <Button variant="primary" size="sm" disabled>
                                {pending.type === "update"
                                    ? "Updating..."
                                    : "Restarting..."}
                            </Button>
                        ) : (
                            <>
                                {canRestart && (
                                    <Button
                                        variant="secondary"
                                        size="sm"
                                        loading={restarting}
                                        onClick={() => restartNode()}
                                    >
                                        <Icon icon={reloadOutline} size="sm" />
                                        Restart
                                    </Button>
                                )}
                                {canUpdate && (
                                    <Button
                                        variant="primary"
                                        size="sm"
                                        loading={restarting}
                                        onClick={() => restartNode(true)}
                                    >
                                        <Icon
                                            icon={cloudDownloadOutline}
                                            size="sm"
                                        />
                                        Update
                                    </Button>
                                )}
                            </>
                        )}
                        <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => window.history.back()}
                        >
                            <Icon icon={arrowBackOutline} size="sm" />
                            Back to Nodes
                        </Button>
                    </>
                }
            />
            <div className="node-show-body">
                <div className="node-show-main">
                    {stats && (
                        <div className="node-show-stats">
                            <StatCard label="Total jobs" value={stats.total} />
                            <StatCard
                                label="Finished"
                                value={stats.finished}
                                style={
                                    stats.finished > 0
                                        ? ["node-show-stat-success"]
                                        : []
                                }
                            />
                            <StatCard
                                label="Errored"
                                value={stats.error}
                                style={
                                    stats.error > 0
                                        ? ["node-show-stat-error"]
                                        : []
                                }
                            />
                            <StatCard
                                label="In flight"
                                value={stats.in_flight}
                            />
                        </div>
                    )}
                    <DetailGrid
                        header={<PanelHeader title="Properties" />}
                        fields={fields}
                        loading={loading}
                    />
                    {(node?.fonts?.length ||
                        node?.capabilities?.includes("dynamic-fonts")) && (
                        <DataTable
                            header={<PanelHeader title="Fonts" />}
                            columns={[
                                {
                                    key: "name",
                                    header: "Name",
                                    render: (font: NodeFontInfo) => (
                                        <span className="node-show-strong">
                                            {font.name}
                                        </span>
                                    )
                                },
                                {
                                    key: "style",
                                    header: "Style",
                                    render: (font: NodeFontInfo) =>
                                        font.style.replace(/_/g, " ")
                                },
                                {
                                    key: "md5",
                                    header: "MD5",
                                    render: (font: NodeFontInfo) => (
                                        <span className="node-show-mono">
                                            {font.md5}
                                        </span>
                                    )
                                },
                                {
                                    key: "url",
                                    header: "URL",
                                    render: (font: NodeFontInfo) => (
                                        <span className="node-show-mono">
                                            {font.url || "-"}
                                        </span>
                                    )
                                },
                                {
                                    key: "size",
                                    header: "Size",
                                    render: (font: NodeFontInfo) => (
                                        <span className="node-show-mono node-show-nowrap">
                                            {`${(font.size / 1024).toFixed(1)} KB`}
                                        </span>
                                    )
                                },
                                {
                                    key: "time",
                                    header: "Installed",
                                    render: (font: NodeFontInfo) => (
                                        <span title={formatTimestamp(font.time)}>
                                            {formatRelativeTime(font.time)}
                                        </span>
                                    )
                                },
                                {
                                    key: "active",
                                    header: "Active",
                                    render: (font: NodeFontInfo) => (
                                        <Status
                                            variant={
                                                font.active ? "success" : "default"
                                            }
                                        >
                                            {font.active ? "Yes" : "No"}
                                        </Status>
                                    )
                                }
                            ]}
                            data={node?.fonts || []}
                            emptyMessage="No fonts installed"
                        />
                    )}
                    {engineEntries.map(([engine, info]) => {
                        const entries = Object.entries(
                            info as Record<string, unknown>
                        );
                        const simpleFields = entries.filter(
                            ([, v]) => !Array.isArray(v)
                        );
                        const arrayFields = entries.filter(([, v]) =>
                            Array.isArray(v)
                        );
                        return (
                            <div key={engine} className="node-show-section">
                                <DetailGrid
                                    header={
                                        <PanelHeader
                                            title={`${
                                                engine.charAt(0).toUpperCase() +
                                                engine.slice(1)
                                            } Engine`}
                                        />
                                    }
                                    fields={simpleFields.map(
                                        ([key, value]) => ({
                                            label: key,
                                            value: String(value)
                                        })
                                    )}
                                />
                                {arrayFields.map(([key, value]) => {
                                    const items = value as Record<
                                        string,
                                        unknown
                                    >[];
                                    if (
                                        items.length === 0 ||
                                        typeof items[0] !== "object"
                                    )
                                        return null;
                                    const headers = Object.keys(items[0]);
                                    return (
                                        <DataTable
                                            key={key}
                                            header={<PanelHeader title={key} />}
                                            columns={headers.map((h) => ({
                                                key: h,
                                                header:
                                                    h.charAt(0).toUpperCase() +
                                                    h.slice(1).replace(/_/g, " "),
                                                render: (
                                                    item: Record<string, unknown>
                                                ) => {
                                                    const v = item[h];
                                                    if (v === true)
                                                        return (
                                                            <Status variant="success">
                                                                Yes
                                                            </Status>
                                                        );
                                                    if (v === false)
                                                        return (
                                                            <Status variant="error">
                                                                No
                                                            </Status>
                                                        );
                                                    return String(v ?? "-") || "-";
                                                }
                                            }))}
                                            data={items}
                                            emptyMessage={`No ${key}`}
                                        />
                                    );
                                })}
                            </div>
                        );
                    })}
                    {node?.libraries && (
                        <Panel title="Libraries">
                            {libraryEntries.length ? (
                                <ul className="node-show-list">
                                    {libraryEntries.map(([library, version]) => (
                                        <li
                                            key={library}
                                            className="node-show-row"
                                        >
                                            {library}
                                            <span className="node-show-mono">
                                                {String(version)}
                                            </span>
                                        </li>
                                    ))}
                                </ul>
                            ) : (
                                <div className="node-show-row node-show-empty">
                                    No libraries
                                </div>
                            )}
                        </Panel>
                    )}
                </div>
                <div className="node-show-side">
                    {update && (
                        <Panel title="Updates" icon={syncOutline}>
                            <div className="node-show-row">
                                <span className="node-show-row-text">
                                    <span className="node-show-strong">
                                        Auto-update
                                    </span>
                                    <span className="node-show-muted">
                                        {update.auto
                                            ? "Enabled, on every start of the node"
                                            : "Disabled"}
                                    </span>
                                </span>
                                <Switch
                                    aria-label="Auto-update"
                                    checked={update.auto}
                                    disabled={!canAutoUpdate || toggling}
                                    onChange={setAutoUpdate}
                                />
                            </div>
                            <div className="node-show-row">
                                <span className="node-show-row-text">
                                    <span className="node-show-strong">
                                        Last update
                                    </span>
                                    <span
                                        className="node-show-muted"
                                        title={formatTimestamp(
                                            update.time ?? undefined
                                        )}
                                    >
                                        {formatRelativeTime(
                                            update.time ?? undefined
                                        )}
                                    </span>
                                </span>
                                {update.status && (
                                    <Status
                                        variant={
                                            update.status === "success"
                                                ? "success"
                                                : update.status === "failure"
                                                  ? "error"
                                                  : "default"
                                        }
                                    >
                                        {update.status}
                                    </Status>
                                )}
                            </div>
                            {update.error && (
                                <div className="node-show-row">
                                    <span className="node-show-row-text">
                                        <span className="node-show-strong">
                                            Update error
                                        </span>
                                        <span className="node-show-error">
                                            {update.error}
                                        </span>
                                    </span>
                                </div>
                            )}
                        </Panel>
                    )}
                    {stats && (
                        <Panel title="Last Job" icon={pulseOutline}>
                            {last ? (
                                <div className="node-show-row">
                                    <span className="node-show-row-text">
                                        <Link
                                            to={`/jobs/${last.id}`}
                                            style={["node-show-strong"]}
                                        >
                                            {last.name || last.id}
                                        </Link>
                                        <span
                                            className="node-show-muted"
                                            title={formatTimestamp(
                                                last.finish_time
                                            )}
                                        >
                                            {formatRelativeTime(
                                                last.finish_time
                                            )}
                                        </span>
                                    </span>
                                    {last.result && (
                                        <Status
                                            variant={
                                                last.result === "success"
                                                    ? "success"
                                                    : last.result === "error"
                                                      ? "error"
                                                      : "default"
                                            }
                                        >
                                            {last.result}
                                        </Status>
                                    )}
                                </div>
                            ) : (
                                <div className="node-show-row node-show-empty">
                                    No jobs printed yet
                                </div>
                            )}
                        </Panel>
                    )}
                    {node && (
                        <Panel
                            title="Capabilities"
                            actions={
                                <span className="node-show-mono">
                                    {capabilities.length}
                                </span>
                            }
                        >
                            <div className="node-show-capabilities">
                                {capabilities.length ? (
                                    capabilities.map((capability) => (
                                        <Tag
                                            key={capability}
                                            style={["node-show-capability"]}
                                        >
                                            {capability}
                                        </Tag>
                                    ))
                                ) : (
                                    <span className="node-show-empty">
                                        No capabilities reported
                                    </span>
                                )}
                            </div>
                        </Panel>
                    )}
                </div>
            </div>
        </div>
    );
};
