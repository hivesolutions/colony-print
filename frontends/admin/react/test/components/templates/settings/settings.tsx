import React, { FC } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import {
    act,
    cleanup,
    fireEvent,
    render,
    screen,
    within
} from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";

import { ColonyPrintAPI } from "../../../../api/colony-print";
import { APIContext, DataContext } from "../../../../contexts";
import { Settings } from "../../../../components/templates/settings/settings";

let location = "";

const MockLocation: FC = () => {
    location = useLocation().pathname;
    return null;
};

describe("SettingsTest", () => {
    let api: ColonyPrintAPI;

    const renderSettings = async (username: string | null = "admin") => {
        const result = render(
            <APIContext.Provider value={api}>
                <DataContext.Provider
                    value={{ username: username, setUsername: () => {} }}
                >
                    <MemoryRouter initialEntries={["/settings"]}>
                        <Settings />
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

    const fields = (container: HTMLElement) =>
        Array.from(container.querySelectorAll(".detail-grid-row")).map(
            (row) => [
                row.querySelector("dt")?.textContent,
                row.querySelector("dd")?.textContent
            ]
        );

    beforeEach(() => {
        location = "";
        api = {
            baseUrl: "",
            sessionId: "preview-session",
            getInfo: vi.fn().mockResolvedValue({
                name: "colony-print",
                version: "0.25.0",
                description: "Colony Print",
                platform: "linux",
                os: "posix",
                python: "3.13.5",
                uptime: 6 * 86400 + 4 * 3600,
                nodes: 5,
                jobs: 0
            }),
            ping: vi.fn().mockResolvedValue({ time: 1 }),
            logout: vi.fn().mockResolvedValue(undefined)
        } as unknown as ColonyPrintAPI;
    });

    afterEach(() => {
        cleanup();
        localStorage.clear();
    });

    test("test_render", async () => {
        const { container } = await renderSettings();
        expect(fields(container)).toEqual([
            ["Name", "colony-print"],
            ["Version", "0.25.0"],
            ["Description", "Colony Print"],
            ["Platform", "linux"],
            ["OS", "posix"],
            ["Python", "3.13.5"],
            ["Uptime", "6d 4h"],
            ["Nodes", "5"],
            ["Jobs", "0"]
        ]);
        const server = screen
            .getByRole("heading", { name: "Server" })
            .closest(".card") as HTMLElement;
        expect(server.querySelector(".status")?.className).toBe(
            "status status-success"
        );
        expect(server.querySelector(".status")?.textContent).toBe("healthy");
        expect(
            screen.getByRole("heading", { name: "API Connection" })
        ).toBeTruthy();
        expect(screen.getByRole("heading", { name: "Session" })).toBeTruthy();
    });

    test("test_render_missing", async () => {
        // the fields not reported by the server are shown as missing
        api.getInfo = vi.fn().mockResolvedValue({ uptime: null });
        const { container } = await renderSettings();
        expect(fields(container)).toEqual([
            ["Name", "-"],
            ["Version", "-"],
            ["Description", "-"],
            ["Platform", "-"],
            ["OS", "-"],
            ["Python", "-"],
            ["Uptime", "-"],
            ["Nodes", "-"],
            ["Jobs", "-"]
        ]);
    });

    test("test_render_loading", () => {
        api.getInfo = vi.fn().mockReturnValue(new Promise(() => {}));
        const { container } = render(
            <APIContext.Provider value={api}>
                <MemoryRouter>
                    <Settings />
                </MemoryRouter>
            </APIContext.Provider>
        );
        expect(container.querySelector(".loader")).toBeTruthy();

        // the health is only known once the server answers
        expect(container.querySelector(".panel-actions")).toBe(null);
    });

    test("test_render_error", async () => {
        api.getInfo = vi.fn().mockRejectedValue(new Error("Offline"));
        api.ping = vi.fn().mockRejectedValue(new Error("Offline"));
        const { container } = await renderSettings();
        expect(fields(container)).toEqual([]);
        const status = container.querySelector(".panel-actions .status");
        expect(status?.className).toBe("status status-error");
        expect(status?.textContent).toBe("unreachable");
    });

    test("test_render_session", async () => {
        // an expired session (whose info is refused) is not shown as
        // an unreachable server, as the health is the one of the ping,
        // as in the side bar shown next to it
        api.getInfo = vi.fn().mockRejectedValue(new Error("Forbidden"));
        const { container } = await renderSettings();
        expect(fields(container)).toEqual([]);
        const status = container.querySelector(".panel-actions .status");
        expect(status?.className).toBe("status status-success");
        expect(status?.textContent).toBe("healthy");
    });

    test("test_save", async () => {
        localStorage.setItem("baseUrl", "https://old.example.com");
        await renderSettings();
        const input = screen.getByLabelText("Base URL") as HTMLInputElement;
        expect(input.value).toBe("https://old.example.com");
        expect(
            screen.getByText(
                "Leave empty to use the server that serves this page."
            )
        ).toBeTruthy();

        fireEvent.change(input, {
            target: { value: "https://print.example.com" }
        });
        fireEvent.click(screen.getByRole("button", { name: "Save" }));
        expect(localStorage.getItem("baseUrl")).toBe(
            "https://print.example.com"
        );
        expect(api.baseUrl).toBe("https://print.example.com");

        // an empty address is saved as well, for the same origin
        fireEvent.change(input, { target: { value: "" } });
        fireEvent.submit(input);
        expect(localStorage.getItem("baseUrl")).toBe("");
        expect(api.baseUrl).toBe("");
    });

    test("test_session", async () => {
        await renderSettings();
        expect(screen.getByText("admin").className).toBe("settings-username");
        expect(screen.getByText("Session ID: preview-session")).toBeTruthy();
    });

    test("test_session_missing", async () => {
        api.sessionId = null;
        await renderSettings(null);
        expect(screen.getByText("-").className).toBe("settings-username");
        expect(screen.getByText("Session ID: -")).toBeTruthy();
    });

    test("test_logout", async () => {
        localStorage.setItem("sessionId", "preview-session");
        await renderSettings();
        const button = screen.getByRole("button", { name: "Log out" });
        expect(button.className).toBe(
            "button button-secondary button-sm settings-logout"
        );

        // the log out is confirmed first, so that it's not done by mistake
        fireEvent.click(button);
        const dialog = screen.getByRole("dialog", {
            name: "Log out of Colony Print?"
        });
        expect(api.logout).not.toHaveBeenCalled();
        expect(localStorage.getItem("sessionId")).toBe("preview-session");
        await act(async () => {
            fireEvent.click(
                within(dialog).getByRole("button", { name: "Log out" })
            );
        });
        expect(api.logout).toHaveBeenCalledTimes(1);
        expect(localStorage.getItem("sessionId")).toBe(null);
        expect(location).toBe("/login");
    });

    test("test_logout_cancel", async () => {
        localStorage.setItem("sessionId", "preview-session");
        await renderSettings(null);
        fireEvent.click(screen.getByRole("button", { name: "Log out" }));
        expect(screen.getByRole("dialog").textContent).toContain(
            "You're signed in as -."
        );
        fireEvent.click(screen.getByRole("button", { name: "Cancel" }));
        expect(screen.queryByRole("dialog")).toBe(null);
        expect(api.logout).not.toHaveBeenCalled();
        expect(localStorage.getItem("sessionId")).toBe("preview-session");
        expect(location).toBe("/settings");
    });
});
