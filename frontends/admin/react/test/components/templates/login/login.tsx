import React, { FC } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import {
    act,
    cleanup,
    fireEvent,
    render,
    screen
} from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { eyeOffOutline, eyeOutline } from "ionicons/icons";

import { ColonyPrintAPI } from "../../../../api/colony-print";
import { APIContext, DataContext } from "../../../../contexts";
import { Login } from "../../../../components/templates/login/login";

let location = "";

const MockLocation: FC = () => {
    location = useLocation().pathname;
    return null;
};

describe("LoginTest", () => {
    let api: ColonyPrintAPI;
    let setUsername: (username: string | null) => void;

    const renderLogin = async () => {
        const result = render(
            <APIContext.Provider value={api}>
                <DataContext.Provider
                    value={{ username: null, setUsername: setUsername }}
                >
                    <MemoryRouter initialEntries={["/login"]}>
                        <Login />
                        <Routes>
                            <Route path="*" element={<MockLocation />} />
                        </Routes>
                    </MemoryRouter>
                </DataContext.Provider>
            </APIContext.Provider>
        );
        await act(async () => {});
        return result;
    };

    const submit = async (username: string, password: string) => {
        fireEvent.change(screen.getByLabelText("Username"), {
            target: { value: username }
        });
        fireEvent.change(screen.getByLabelText("Password"), {
            target: { value: password }
        });
        await act(async () => {
            fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
        });
    };

    const status = (container: HTMLElement) => [
        container.querySelector(".login-status-label")?.textContent,
        container.querySelector(".login-status-dot")?.className
    ];

    const openServer = () =>
        fireEvent.click(screen.getByRole("button", { name: /^Server/ }));

    beforeEach(() => {
        location = "";
        setUsername = vi.fn();
        api = {
            baseUrl: "",
            login: vi.fn().mockResolvedValue({
                session_id: "sid",
                username: "admin"
            }),
            ping: vi.fn().mockResolvedValue({ time: 1 })
        } as unknown as ColonyPrintAPI;
    });

    afterEach(() => {
        cleanup();
        localStorage.clear();
    });

    test("test_render", async () => {
        const { container } = await renderLogin();
        const heading = screen.getByRole("heading", { name: "Colony Print" });
        expect(heading.className).toBe("login-brand");
        expect(heading.tagName).toBe("H1");

        // the logo is large enough for its sliced logotype, drawn in
        // white in the dark panel of the brand
        expect(heading.querySelector("svg")?.getAttribute("height")).toBe("48");
        expect(heading.querySelectorAll("clipPath").length).toBe(3);
        expect(heading.closest("section")?.className).toBe("login-hero");
        expect(screen.getByRole("heading", { name: "Sign in" }).tagName).toBe(
            "H2"
        );
        expect(screen.getByLabelText("Password").getAttribute("type")).toBe(
            "password"
        );
        expect(document.activeElement).toBe(screen.getByLabelText("Username"));
        expect(container.querySelector(".error-box")).toBe(null);

        // the server is the one serving the page, as no address is set
        expect(status(container)).toEqual([
            "API healthy",
            "login-status-dot login-status-healthy"
        ]);
        expect(
            container.querySelector(".login-status-server")?.textContent
        ).toBe(window.location.host);
    });

    test("test_health", async () => {
        // the health is unknown until the server answers its ping
        api.ping = vi.fn().mockReturnValue(new Promise(() => {}));
        const { container } = await renderLogin();
        expect(status(container)).toEqual([
            "Connecting",
            "login-status-dot login-status-loading"
        ]);
    });

    test("test_health_unreachable", async () => {
        api.ping = vi.fn().mockRejectedValue(new Error("Offline"));
        const { container } = await renderLogin();
        expect(status(container)).toEqual([
            "API unreachable",
            "login-status-dot login-status-unreachable"
        ]);
    });

    test("test_health_stale", async () => {
        // the health of a server whose address was changed meanwhile is
        // ignored once known, the one of the new server being shown
        let resolve: (value: unknown) => void = () => {};
        api.ping = vi
            .fn()
            .mockReturnValueOnce(new Promise((r) => (resolve = r)))
            .mockRejectedValue(new Error("Offline"));
        const { container } = await renderLogin();
        openServer();
        const input = screen.getByLabelText("Server address");
        fireEvent.change(input, {
            target: { value: "https://other.example.com" }
        });
        await act(async () => {
            fireEvent.blur(input);
        });
        await act(async () => {
            resolve({ time: 1 });
        });
        expect(status(container)).toEqual([
            "API unreachable",
            "login-status-dot login-status-unreachable"
        ]);
    });

    test("test_save_base_url", async () => {
        localStorage.setItem("baseUrl", "https://print.example.com");
        api.baseUrl = "https://print.example.com";
        const { container } = await renderLogin();
        const toggle = screen.getByRole("button", { name: /^Server/ });
        expect(toggle.getAttribute("aria-expanded")).toBe("false");
        expect(toggle.textContent).toBe("Serverhttps://print.example.com");
        expect(screen.queryByLabelText("Server address")).toBe(null);

        openServer();
        expect(toggle.getAttribute("aria-expanded")).toBe("true");
        expect(toggle.getAttribute("aria-controls")).toBe("login-server");
        expect(toggle.querySelector("ion-icon")?.getAttribute("class")).toBe(
            "icon icon-sm login-server-open"
        );
        const input = screen.getByLabelText(
            "Server address"
        ) as HTMLInputElement;
        expect(input.value).toBe("https://print.example.com");

        // the address is applied once left, as in the settings, and the
        // health of the new server is checked
        fireEvent.change(input, {
            target: { value: "https://other.example.com" }
        });
        expect(api.baseUrl).toBe("https://print.example.com");
        await act(async () => {
            fireEvent.blur(input);
        });
        expect(api.baseUrl).toBe("https://other.example.com");
        expect(localStorage.getItem("baseUrl")).toBe(
            "https://other.example.com"
        );
        expect(api.ping).toHaveBeenCalledTimes(2);
        expect(
            container.querySelector(".login-status-server")?.textContent
        ).toBe("https://other.example.com");

        // while the same address is not applied (nor checked) again
        await act(async () => {
            fireEvent.blur(input);
        });
        expect(api.ping).toHaveBeenCalledTimes(2);

        openServer();
        expect(screen.queryByLabelText("Server address")).toBe(null);
    });

    test("test_login", async () => {
        await renderLogin();
        await submit("admin", "secret");
        expect(api.login).toHaveBeenCalledWith("admin", "secret");
        expect(localStorage.getItem("sessionId")).toBe("sid");
        expect(localStorage.getItem("username")).toBe("admin");
        expect(setUsername).toHaveBeenCalledWith("admin");
        expect(location).toBe("/");

        // without a change of the server, its address is not set
        expect(localStorage.getItem("baseUrl")).toBe(null);
        expect(api.ping).toHaveBeenCalledTimes(1);
    });

    test("test_login_base_url", async () => {
        // the address typed and not yet applied is applied on the sign
        // in, so that the login is sent to that server
        api.login = vi.fn().mockImplementation(async () => {
            expect(api.baseUrl).toBe("https://other.example.com");
            return { session_id: "sid", username: "admin" };
        });
        await renderLogin();
        openServer();
        fireEvent.change(screen.getByLabelText("Server address"), {
            target: { value: "https://other.example.com" }
        });
        await submit("admin", "secret");
        expect(api.login).toHaveBeenCalledTimes(1);
        expect(localStorage.getItem("baseUrl")).toBe(
            "https://other.example.com"
        );
        expect(location).toBe("/");
    });

    test("test_login_error", async () => {
        api.login = vi.fn().mockRejectedValue(new Error("Invalid credentials"));
        const { container } = await renderLogin();
        await submit("admin", "wrong");
        expect(container.querySelector(".error-box")?.textContent).toBe(
            "Invalid credentials"
        );
        expect(localStorage.getItem("sessionId")).toBe(null);
        expect(setUsername).not.toHaveBeenCalled();
        expect(location).toBe("/login");

        // the button is enabled again, for another attempt
        expect(
            (
                screen.getByRole("button", {
                    name: "Sign in"
                }) as HTMLButtonElement
            ).disabled
        ).toBe(false);
    });

    test("test_login_unknown_error", async () => {
        // an error that is not an instance of Error has no message
        // that can be shown, so a generic one is shown instead
        api.login = vi.fn().mockRejectedValue("failure");
        await renderLogin();
        await submit("admin", "wrong");
        expect(screen.getByText("Login failed")).toBeTruthy();
    });

    test("test_login_pending", async () => {
        let resolve: (value: unknown) => void = () => {};
        api.login = vi.fn().mockReturnValue(new Promise((r) => (resolve = r)));
        await renderLogin();
        fireEvent.click(screen.getByRole("button", { name: "Sign in" }));
        const button = screen.getByRole("button", {
            name: "Loading..."
        }) as HTMLButtonElement;
        expect(button.disabled).toBe(true);
        await act(async () => {
            resolve({ session_id: "sid", username: "admin" });
        });
        expect(location).toBe("/");
    });

    test("test_password", async () => {
        await renderLogin();
        const input = screen.getByLabelText("Password");
        const toggle = screen.getByRole("button", { name: "Show password" });
        expect(toggle.getAttribute("aria-pressed")).toBe("false");
        expect(toggle.getAttribute("type")).toBe("button");
        expect(toggle.querySelector("ion-icon")?.getAttribute("icon")).toBe(
            eyeOutline
        );

        // the password is shown (and hidden again) without submitting
        fireEvent.click(toggle);
        expect(input.getAttribute("type")).toBe("text");
        expect(toggle.getAttribute("aria-label")).toBe("Hide password");
        expect(toggle.getAttribute("aria-pressed")).toBe("true");
        expect(toggle.querySelector("ion-icon")?.getAttribute("icon")).toBe(
            eyeOffOutline
        );
        fireEvent.click(toggle);
        expect(input.getAttribute("type")).toBe("password");
        expect(api.login).not.toHaveBeenCalled();
    });
});
