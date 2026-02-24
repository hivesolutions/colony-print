import React, { FC, useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";

import { useAPI } from "../../../hooks";
import { NodeInfo } from "../../../api/colony-print";
import { Button, Tag, Title, Text } from "../../atoms";
import { ContentHeader, DetailGrid } from "../../molecules";

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
            {engineEntries.map(([engine, info]) => (
                <div key={engine} className="node-show-section">
                    <Title level={3}>
                        {engine.charAt(0).toUpperCase() +
                            engine.slice(1)}{" "}
                        Engine
                    </Title>
                    <DetailGrid
                        fields={Object.entries(
                            info as Record<string, unknown>
                        ).map(([key, value]) => ({
                            label: key,
                            value: (
                                <Text>
                                    {typeof value === "object"
                                        ? JSON.stringify(value, null, 2)
                                        : String(value)}
                                </Text>
                            )
                        }))}
                    />
                </div>
            ))}
        </div>
    );
};
