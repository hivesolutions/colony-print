import React, {
    FC,
    useCallback,
    useEffect,
    useRef,
    useState
} from "react";
import { useParams } from "react-router-dom";

import { useAPI } from "../../../hooks";
import {
    JobInfo,
    NodeInfo,
    NodeFontInfo
} from "../../../api/colony-print";
import { Button, Link, Tag, Title, Text } from "../../atoms";
import {
    ContentHeader,
    DataTable,
    DetailGrid,
    StatCard
} from "../../molecules";
import {
    formatRelativeTime,
    formatTimestamp,
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

    const fetchNode = useCallback(
        async (silent = false) => {
            if (!id) return;
            if (!silent) setLoading(true);
            try {
                const data = await api.getNode(id);
                setNode(data);
            } catch {
                setNode(null);
            } finally {
                setLoading(false);
            }

            // retrieves the job (restart or update) that is going to
            // restart the node, if any, as the node doesn't get another
            // one while it's queued or in flight
            try {
                const jobs = await api.listJobs();
                setPending(
                    Object.values(jobs).find(
                        (job) =>
                            job.node_id === id && isRestartPending(job)
                    ) || null
                );
            } catch {
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

    // keeps the identifier of the node that is being shown, so that
    // the wait for a change of the node stops once another node is
    // shown (or the view is gone)
    const shownId = useRef<string | undefined>(id);
    useEffect(() => {
        shownId.current = id;
        return () => {
            shownId.current = undefined;
        };
    }, [id]);

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
              { label: "ID", value: id || "-" },
              { label: "Name", value: node.name || "-" },
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
                  value: (node.engines || []).join(", ") || "-"
              },
              {
                  label: "Capabilities",
                  value: node.capabilities?.length ? (
                      <div className="node-show-tags">
                          {node.capabilities.map((capability) => (
                              <Tag key={capability}>{capability}</Tag>
                          ))}
                      </div>
                  ) : (
                      "-"
                  )
              },
              { label: "Platform", value: node.platform || "-" },
              { label: "OS", value: node.os || "-" },
              ...systemFields,
              { label: "Version", value: node.version || "-" },
              {
                  label: "Started",
                  value: formatTimestamp(node.start_time)
              },
              {
                  label: "Last Seen",
                  value: formatRelativeTime(node.last_ping)
              }
          ]
        : [];

    const engineEntries = node?.engine_info
        ? Object.entries(node.engine_info)
        : [];

    const libraryEntries = node?.libraries
        ? Object.entries(node.libraries)
        : [];

    const libraryColumns = [
        {
            key: "library",
            header: "Library",
            render: ([library]: [string, string]) => library
        },
        {
            key: "version",
            header: "Version",
            render: ([, version]: [string, string]) =>
                String(version)
        }
    ];

    const stats = node?.stats;
    const last = stats?.last;

    const lastFields = [
        {
            label: "Last print",
            value: last ? (
                <span className="node-show-last">
                    {formatRelativeTime(last.finish_time)}
                    {last.result && (
                        <Tag
                            variant={
                                (last.result === "success"
                                    ? "success"
                                    : last.result === "error"
                                      ? "error"
                                      : "default") as
                                    | "success"
                                    | "error"
                                    | "default"
                            }
                        >
                            {last.result}
                        </Tag>
                    )}
                </span>
            ) : (
                "-"
            )
        },
        {
            label: "Last job",
            value: last ? (
                <Link to={`/jobs/${last.id}`}>
                    {last.name || last.id}
                </Link>
            ) : (
                "-"
            )
        }
    ];

    const update = node?.update;

    const updateFields = update
        ? [
              {
                  label: "Auto-update",
                  value: (
                      <span className="node-show-update">
                          <Tag
                              variant={update.auto ? "success" : "default"}
                          >
                              {update.auto ? "Enabled" : "Disabled"}
                          </Tag>
                          {canAutoUpdate && (
                              <Button
                                  variant="secondary"
                                  size="sm"
                                  loading={toggling}
                                  onClick={() =>
                                      setAutoUpdate(!update.auto)
                                  }
                              >
                                  {update.auto ? "Disable" : "Enable"}
                              </Button>
                          )}
                      </span>
                  )
              },
              {
                  label: "Last update",
                  value: (
                      <span className="node-show-update">
                          {formatRelativeTime(update.time ?? undefined)}
                          {update.status && (
                              <Tag
                                  variant={
                                      (update.status === "success"
                                          ? "success"
                                          : update.status === "failure"
                                            ? "error"
                                            : "default") as
                                          | "success"
                                          | "error"
                                          | "default"
                                  }
                              >
                                  {update.status}
                              </Tag>
                          )}
                      </span>
                  )
              },
              ...(update.error
                  ? [{ label: "Update error", value: update.error }]
                  : [])
          ]
        : [];

    return (
        <div className="node-show">
            <ContentHeader
                title={node?.name || "Node"}
                description={id ? `Node ${id}` : undefined}
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
                                        variant="primary"
                                        size="sm"
                                        loading={restarting}
                                        onClick={() => restartNode()}
                                    >
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
                            Back to Nodes
                        </Button>
                    </>
                }
            />
            {stats && (
                <div className="node-show-stats">
                    <StatCard
                        label="Total jobs"
                        value={stats.total}
                    />
                    <StatCard
                        label="Finished"
                        value={stats.finished}
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
            <DetailGrid fields={fields} loading={loading} />
            {stats && (
                <div className="node-show-section">
                    <Title level={3}>Print Diagnostics</Title>
                    <DetailGrid fields={lastFields} />
                </div>
            )}
            {update && (
                <div className="node-show-section">
                    <Title level={3}>Update</Title>
                    <DetailGrid fields={updateFields} />
                </div>
            )}
            {(node?.fonts?.length ||
                node?.capabilities?.includes("dynamic-fonts")) && (
                <div className="node-show-section">
                    <Title level={3}>Fonts</Title>
                    <DataTable
                        columns={[
                            {
                                key: "name",
                                header: "Name",
                                render: (font: NodeFontInfo) => font.name
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
                                render: (font: NodeFontInfo) => font.md5
                            },
                            {
                                key: "url",
                                header: "URL",
                                render: (font: NodeFontInfo) => font.url || "-"
                            },
                            {
                                key: "size",
                                header: "Size",
                                render: (font: NodeFontInfo) =>
                                    `${(font.size / 1024).toFixed(1)} KB`
                            },
                            {
                                key: "time",
                                header: "Installed",
                                render: (font: NodeFontInfo) =>
                                    formatRelativeTime(font.time)
                            },
                            {
                                key: "active",
                                header: "Active",
                                render: (font: NodeFontInfo) => (
                                    <Tag
                                        variant={
                                            font.active ? "success" : "default"
                                        }
                                    >
                                        {font.active ? "Yes" : "No"}
                                    </Tag>
                                )
                            }
                        ]}
                        data={node?.fonts || []}
                        emptyMessage="No fonts installed"
                    />
                </div>
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
                        <Title level={3}>
                            {engine.charAt(0).toUpperCase() +
                                engine.slice(1)}{" "}
                            Engine
                        </Title>
                        {simpleFields.length > 0 && (
                            <DetailGrid
                                fields={simpleFields.map(
                                    ([key, value]) => ({
                                        label: key,
                                        value: String(value)
                                    })
                                )}
                            />
                        )}
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
                                <div
                                    key={key}
                                    className="node-show-subsection"
                                >
                                    <Text variant="secondary">
                                        {key}
                                    </Text>
                                    <DataTable
                                        columns={headers.map(
                                            (h) => ({
                                                key: h,
                                                header:
                                                    h
                                                        .charAt(0)
                                                        .toUpperCase() +
                                                    h
                                                        .slice(1)
                                                        .replace(
                                                            /_/g,
                                                            " "
                                                        ),
                                                render: (
                                                    item: Record<
                                                        string,
                                                        unknown
                                                    >
                                                ) => {
                                                    const v =
                                                        item[h];
                                                    if (
                                                        v === true
                                                    )
                                                        return (
                                                            <Tag variant="success">
                                                                Yes
                                                            </Tag>
                                                        );
                                                    if (
                                                        v === false
                                                    )
                                                        return (
                                                            <Tag variant="error">
                                                                No
                                                            </Tag>
                                                        );
                                                    return (
                                                        String(
                                                            v ?? "-"
                                                        ) || "-"
                                                    );
                                                }
                                            })
                                        )}
                                        data={items}
                                        emptyMessage={`No ${key}`}
                                    />
                                </div>
                            );
                        })}
                    </div>
                );
            })}
            {node?.libraries && (
                <div className="node-show-section">
                    <Title level={3}>Libraries</Title>
                    <DataTable
                        columns={libraryColumns}
                        data={libraryEntries}
                        emptyMessage="No libraries"
                    />
                </div>
            )}
        </div>
    );
};
