import React, { FC, useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { useAPI } from "../../../hooks";
import { NodeInfo } from "../../../api/colony-print";
import { Button, Tag, Title, Text } from "../../atoms";
import { ContentHeader, DataTable, DetailGrid } from "../../molecules";

import "./node-show.css";

export const NodeShow: FC = () => {
    const api = useAPI();
    const { id } = useParams<{ id: string }>();
    const [node, setNode] = useState<NodeInfo | null>(null);
    const [loading, setLoading] = useState(true);

    const fetchNode = useCallback(async () => {
        if (!id) return;
        setLoading(true);
        try {
            const data = await api.getNode(id);
            setNode(data);
        } catch {
            setNode(null);
        } finally {
            setLoading(false);
        }
    }, [api, id]);

    useEffect(() => {
        fetchNode();
    }, [fetchNode]);

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
              { label: "Platform", value: node.platform || "-" },
              { label: "OS", value: node.os || "-" },
              { label: "Version", value: node.version || "-" }
          ]
        : [];

    const engineEntries = node?.engine_info
        ? Object.entries(node.engine_info)
        : [];

    return (
        <div className="node-show">
            <ContentHeader
                title={node?.name || "Node"}
                description={id ? `Node ${id}` : undefined}
                actions={
                    <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => window.history.back()}
                    >
                        Back to Nodes
                    </Button>
                }
            />
            <DetailGrid fields={fields} loading={loading} />
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
        </div>
    );
};
