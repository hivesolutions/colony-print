import React, {
    FC,
    FormEvent,
    useCallback,
    useContext,
    useEffect,
    useRef,
    useState
} from "react";
import { useNavigate } from "react-router-dom";
import {
    chevronForwardOutline,
    eyeOffOutline,
    eyeOutline
} from "ionicons/icons";

import { useAPI } from "../../../hooks";
import { DataContext } from "../../../contexts";
import { Button, Icon, Logo, Text, TextInput, Title } from "../../atoms";
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
    const [showPassword, setShowPassword] = useState(false);
    const [showServer, setShowServer] = useState(false);
    const [baseUrl, setBaseUrl] = useState(
        localStorage.getItem("baseUrl") ?? ""
    );
    const [server, setServer] = useState(api.baseUrl);
    const [healthy, setHealthy] = useState<boolean | null>(null);

    // keeps the number of the last health check, so that the one of a
    // server that is not used anymore (as its address was changed in the
    // meantime) is ignored once done, instead of replacing the current one
    const check = useRef(0);

    // the health of the server is the one of its (public) ping, so that
    // a server that can't be reached is told apart from a failed login
    const fetchHealth = useCallback(async () => {
        const current = ++check.current;
        setHealthy(null);
        const pingData = await api.ping().catch(() => null);
        if (check.current !== current) return;
        setHealthy(pingData !== null);
    }, [api]);

    useEffect(() => {
        fetchHealth();
    }, [fetchHealth]);

    // applies the address of the server as the settings do, checking the
    // health of the new server, the login being sent to it
    const onSaveBaseUrl = () => {
        if (api.baseUrl === baseUrl) return;
        localStorage.setItem("baseUrl", baseUrl);
        api.baseUrl = baseUrl;
        setServer(baseUrl);
        fetchHealth();
    };

    const onSubmit = async (e: FormEvent) => {
        e.preventDefault();
        onSaveBaseUrl();
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

    const status =
        healthy === null
            ? "loading"
            : healthy
              ? "healthy"
              : "unreachable";

    return (
        <div className="login-page">
            <section className="login-hero" aria-label="Colony Print">
                <h1 className="login-brand">
                    <Logo height={48} />
                </h1>
                <div className="login-pitch">
                    <p className="login-tagline">
                        The print nodes, their jobs and printers, in one
                        console.
                    </p>
                    <Text variant="secondary" style={["login-subtitle"]}>
                        Sign in with an administrator account of this Colony
                        Print server.
                    </Text>
                </div>
                <div className="login-status">
                    <span className="login-status-label">
                        <span
                            className={`login-status-dot login-status-${status}`}
                        />
                        {healthy === null
                            ? "Connecting"
                            : healthy
                              ? "API healthy"
                              : "API unreachable"}
                    </span>
                    <span className="login-status-server">
                        {server || window.location.host}
                    </span>
                </div>
            </section>
            <main className="login-main">
                <Form onSubmit={onSubmit} style={["login-form"]}>
                    <div className="login-header">
                        <Title level={2}>Sign in</Title>
                        <Text variant="secondary">
                            Welcome back, sign in to manage the
                            infrastructure.
                        </Text>
                    </div>
                    {error && <ErrorBox message={error} />}
                    <TextInput
                        id="username"
                        label="Username"
                        placeholder="Enter your username"
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        autoFocus
                    />
                    <div className="login-password">
                        <TextInput
                            id="password"
                            label="Password"
                            type={showPassword ? "text" : "password"}
                            placeholder="Enter your password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                        />
                        <button
                            className="login-reveal"
                            type="button"
                            onClick={() => setShowPassword(!showPassword)}
                            aria-label={
                                showPassword ? "Hide password" : "Show password"
                            }
                        >
                            <Icon
                                icon={showPassword ? eyeOffOutline : eyeOutline}
                            />
                        </button>
                    </div>
                    <div className="login-server">
                        <button
                            className="login-server-toggle"
                            type="button"
                            onClick={() => setShowServer(!showServer)}
                            aria-expanded={showServer}
                            aria-controls="login-server"
                        >
                            <Icon
                                icon={chevronForwardOutline}
                                size="sm"
                                style={showServer ? ["login-server-open"] : []}
                            />
                            Server
                            <span className="login-server-value">
                                {server || window.location.host}
                            </span>
                        </button>
                        {showServer && (
                            <div
                                id="login-server"
                                className="login-server-field"
                            >
                                <TextInput
                                    id="base-url"
                                    aria-label="Server address"
                                    placeholder="Leave empty for same origin"
                                    value={baseUrl}
                                    onChange={(e) => setBaseUrl(e.target.value)}
                                    onBlur={onSaveBaseUrl}
                                    style={["login-server-input"]}
                                />
                                <Text variant="small">
                                    The Colony Print server to sign in to, the
                                    one serving this page when empty.
                                </Text>
                            </div>
                        )}
                    </div>
                    <Button type="submit" loading={loading}>
                        Sign in
                    </Button>
                </Form>
            </main>
        </div>
    );
};
