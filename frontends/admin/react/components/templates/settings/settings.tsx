import React, { FC, useCallback, useContext, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAPI } from "../../../hooks";
import { ServerInfo } from "../../../api/colony-print";
import { DataContext } from "../../../contexts";
import { Button, Card, Tag, Text, TextInput, Title } from "../../atoms";
import { ContentHeader, DetailGrid, Form } from "../../molecules";

import { formatDuration } from "../../../utils";

import "./settings.css";

export const Settings: FC = () => {
    const api = useAPI();
    const navigate = useNavigate();
    const { username, setUsername } = useContext(DataContext);

    const [baseUrl, setBaseUrl] = useState(
        localStorage.getItem("baseUrl") ?? ""
    );
    const [serverInfo, setServerInfo] = useState<ServerInfo | null>(null);
    const [serverLoading, setServerLoading] = useState(true);

    const fetchServerInfo = useCallback(async () => {
        setServerLoading(true);
        try {
            const data = await api.getInfo();
            setServerInfo(data);
        } catch {
            setServerInfo(null);
        } finally {
            setServerLoading(false);
        }
    }, [api]);

    useEffect(() => {
        fetchServerInfo();
    }, [fetchServerInfo]);

    const onSaveBaseUrl = () => {
        localStorage.setItem("baseUrl", baseUrl);
        api.baseUrl = baseUrl;
    };

    const onLogout = async () => {
        try {
            await api.logout();
        } catch {
            // ignore logout errors
        }
        localStorage.removeItem("sessionId");
        localStorage.removeItem("username");
        api.sessionId = null;
        api.username = null;
        setUsername(null);
        navigate("/login", { replace: true });
    };

    return (
        <div className="settings">
            <ContentHeader
                title="Settings"
                description="Configure your admin interface"
            />
            <DetailGrid
                fields={
                    serverInfo
                        ? [
                              {
                                  label: "Name",
                                  value: serverInfo.name || "-"
                              },
                              {
                                  label: "Version",
                                  value: (
                                      <Tag variant="default">
                                          {serverInfo.version}
                                      </Tag>
                                  )
                              },
                              {
                                  label: "Description",
                                  value:
                                      serverInfo.description || "-"
                              },
                              {
                                  label: "Platform",
                                  value: serverInfo.platform || "-"
                              },
                              {
                                  label: "OS",
                                  value: serverInfo.os || "-"
                              },
                              {
                                  label: "Python",
                                  value: serverInfo.python || "-"
                              },
                              {
                                  label: "Uptime",
                                  value: formatDuration(
                                      serverInfo.uptime
                                  )
                              },
                              {
                                  label: "Nodes",
                                  value: String(
                                      serverInfo.nodes ?? "-"
                                  )
                              },
                              {
                                  label: "Jobs",
                                  value: String(
                                      serverInfo.jobs ?? "-"
                                  )
                              }
                          ]
                        : []
                }
                loading={serverLoading}
            />
            <Card style={["settings-section"]}>
                <Title level={3}>API Connection</Title>
                <Form
                    onSubmit={(e) => {
                        e.preventDefault();
                        onSaveBaseUrl();
                    }}
                >
                    <TextInput
                        id="base-url"
                        label="Base URL"
                        placeholder="Leave empty for same origin"
                        value={baseUrl}
                        onChange={(e) => setBaseUrl(e.target.value)}
                    />
                    <Button type="submit" size="sm">
                        Save
                    </Button>
                </Form>
            </Card>
            <Card style={["settings-section"]}>
                <Title level={3}>Session</Title>
                <div className="settings-session-info">
                    <Text variant="secondary">
                        Signed in as: {username || "-"}
                    </Text>
                    <Text variant="small">
                        Session ID: {api.sessionId || "-"}
                    </Text>
                </div>
                <Button
                    variant="danger"
                    size="sm"
                    onClick={onLogout}
                >
                    Sign out
                </Button>
            </Card>
        </div>
    );
};
