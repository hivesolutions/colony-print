import React, { FC, useContext, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAPI } from "../../../hooks";
import { DataContext } from "../../../contexts";
import { Button, Card, Text, TextInput, Title } from "../../atoms";
import { ContentHeader, Form } from "../../molecules";

import "./settings.css";

export const Settings: FC = () => {
    const api = useAPI();
    const navigate = useNavigate();
    const { username, setUsername } = useContext(DataContext);

    const [baseUrl, setBaseUrl] = useState(
        localStorage.getItem("baseUrl") ?? ""
    );

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
