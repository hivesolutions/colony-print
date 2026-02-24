import React, { FC, FormEvent, useContext, useState } from "react";
import { useNavigate } from "react-router-dom";

import { useAPI } from "../../../hooks";
import { DataContext } from "../../../contexts";
import { Button, Card, TextInput, Title } from "../../atoms";
import { ErrorBox, Form } from "../../molecules";

import "./login.css";

export const Login: FC = () => {
    const api = useAPI();
    const navigate = useNavigate();
    const { setUsername: setGlobalUsername } = useContext(DataContext);

    const [username, setUsername] = useState("");
    const [password, setPassword] = useState("");
    const [error, setError] = useState<string | null>(null);
    const [loading, setLoading] = useState(false);

    const onSubmit = async (e: FormEvent) => {
        e.preventDefault();
        setError(null);
        setLoading(true);
        try {
            const result = await api.login(username, password);
            localStorage.setItem("sessionId", result.session_id);
            localStorage.setItem("username", result.username);
            setGlobalUsername(result.username);
            navigate("/", { replace: true });
        } catch (err) {
            const message =
                err instanceof Error ? err.message : "Login failed";
            setError(message);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="login-page">
            <Card style={["login-card"]}>
                <Title level={2}>Colony Print</Title>
                <Form onSubmit={onSubmit}>
                    {error && <ErrorBox message={error} />}
                    <TextInput
                        id="username"
                        label="Username"
                        placeholder="Enter your username"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        autoFocus
                    />
                    <TextInput
                        id="password"
                        label="Password"
                        type="password"
                        placeholder="Enter your password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                    />
                    <Button type="submit" loading={loading}>
                        Sign in
                    </Button>
                </Form>
            </Card>
        </div>
    );
};
