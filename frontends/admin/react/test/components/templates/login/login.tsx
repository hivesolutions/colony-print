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

    const renderLogin = () =>
        render(
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

    beforeEach(() => {
        location = "";
        setUsername = vi.fn();
        api = {
            login: vi.fn().mockResolvedValue({
                session_id: "sid",
                username: "admin"
            })
        } as unknown as ColonyPrintAPI;
    });

    afterEach(() => {
        cleanup();
        localStorage.clear();
    });

    test("test_render", () => {
        renderLogin();
        const heading = screen.getByRole("heading", { name: "Colony Print" });
        expect(heading.className).toBe("login-brand");
        expect(heading.querySelector("svg")?.getAttribute("height")).toBe("48");

        // the logotype is drawn sliced, as the login is large enough
        // for its cuts, with the middle slice in the brand mint
        expect(heading.querySelectorAll("clipPath").length).toBe(3);
        expect(screen.getByLabelText("Password").getAttribute("type")).toBe(
            "password"
        );
        expect(document.activeElement).toBe(screen.getByLabelText("Username"));
        expect(screen.queryByRole("alert")).toBe(null);
    });

    test("test_login", async () => {
        renderLogin();
        await submit("admin", "secret");
        expect(api.login).toHaveBeenCalledWith("admin", "secret");
        expect(localStorage.getItem("sessionId")).toBe("sid");
        expect(localStorage.getItem("username")).toBe("admin");
        expect(setUsername).toHaveBeenCalledWith("admin");
        expect(location).toBe("/");
    });

    test("test_login_error", async () => {
        api.login = vi.fn().mockRejectedValue(new Error("Invalid credentials"));
        renderLogin();
        await submit("admin", "wrong");
        expect(screen.getByText("Invalid credentials")).toBeTruthy();
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
        renderLogin();
        await submit("admin", "wrong");
        expect(screen.getByText("Login failed")).toBeTruthy();
    });

    test("test_login_pending", async () => {
        let resolve: (value: unknown) => void = () => {};
        api.login = vi.fn().mockReturnValue(new Promise((r) => (resolve = r)));
        renderLogin();
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
});
