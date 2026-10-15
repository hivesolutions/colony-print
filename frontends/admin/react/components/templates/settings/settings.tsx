import React, { FC, useCallback, useContext, useEffect, useState } from "react";
import { logOutOutline } from "ionicons/icons";

import { useAPI, useLogout } from "../../../hooks";
import { ServerInfo } from "../../../api/colony-print";
import { DataContext } from "../../../contexts";
import { Button, Icon, Label, Status, Text, TextInput } from "../../atoms";
import {
    ContentHeader,
    DetailGrid,
    Form,
    Panel,
    PanelHeader
} from "../../molecules";

import { formatDuration } from "../../../utils";

import "./settings.css";

export const Settings: FC = () => {
    const api = useAPI();
    const onLogout = useLogout();
    const { username } = useContext(DataContext);

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

    return (
        <div className="settings">
            <ContentHeader
                title="Settings"
                description="Configure your admin interface"
            />
            <div className="settings-body">
                <div className="settings-server">
                    <DetailGrid
                        header={
                            <PanelHeader
                                title="Server"
                                actions={
                                    !serverLoading && (
                                        <Status
                                            variant={
                                                serverInfo ? "success" : "error"
                                            }
                                        >
                                            {serverInfo
                                                ? "healthy"
                                                : "unavailable"}
                                        </Status>
                                    )
                                }
                            />
                        }
                        fields={
                            serverInfo
                                ? [
                                      {
                                          label: "Name",
                                          value: serverInfo.name || "-"
                                      },
                                      {
                                          label: "Version",
                                          value: serverInfo.version || "-"
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
                </div>
                <div className="settings-side">
                    <Panel title="API Connection">
                        <Form
                            style={["settings-form"]}
                            onSubmit={(e) => {
                                e.preventDefault();
                                onSaveBaseUrl();
                            }}
                        >
                            <Label htmlFor="base-url">Base URL</Label>
                            <div className="settings-url">
                                <TextInput
                                    id="base-url"
                                    placeholder="Leave empty for same origin"
                                    value={baseUrl}
                                    onChange={(e) => setBaseUrl(e.target.value)}
                                    style={["settings-url-input"]}
                                />
                                <Button type="submit" size="sm">
                                    Save
                                </Button>
                            </div>
                            <Text variant="small">
                                Leave empty to use the server that serves
                                this page.
                            </Text>
                        </Form>
                    </Panel>
                    <Panel title="Session">
                        <div className="settings-session">
                            <div className="settings-session-info">
                                <Text>
                                    Signed in as{" "}
                                    <span className="settings-username">
                                        {username || "-"}
                                    </span>
                                </Text>
                                <Text variant="small">
                                    Session ID: {api.sessionId || "-"}
                                </Text>
                            </div>
                            <Button
                                variant="secondary"
                                size="sm"
                                onClick={onLogout}
                                style={["settings-logout"]}
                            >
                                <Icon icon={logOutOutline} size="sm" />
                                Log out
                            </Button>
                        </div>
                    </Panel>
                </div>
            </div>
        </div>
    );
};
