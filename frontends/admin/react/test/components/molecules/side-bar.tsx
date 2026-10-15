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
import { documentTextOutline, serverOutline } from "ionicons/icons";

import { ColonyPrintAPI } from "../../../api/colony-print";
import { APIContext, DataContext } from "../../../contexts";
import { SideBar } from "../../../components/molecules";

const NOW = Date.now() / 1000;

let location = "";

const MockLocation: FC = () => {
    location = useLocation().pathname;
    return null;
};

describe("SideBarTest", () => {
    let api: ColonyPrintAPI;

    const renderBar = async (
        path: string,
        options: {
            open?: boolean;
            onClose?: () => void;
            username?: string | null;
        } = {}
    ) => {
        const result = render(
            <APIContext.Provider value={api}>
                <DataContext.Provider
                    value={{
                        username:
                            options.username === undefined
                                ? "admin"
                                : options.username,
                        setUsername: () => {}
                    }}
                >
                    <MemoryRouter initialEntries={[path]}>
                        <SideBar
                            open={options.open}
                            onClose={options.onClose}
                        />
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

    beforeEach(() => {
        location = "";
        api = {
            ping: vi.fn().mockResolvedValue({ time: 1 }),
            getInfo: vi.fn().mockResolvedValue({
                version: "0.25.0",
                uptime: 6 * 86400 + 4 * 3600
            }),
            listNodes: vi.fn().mockResolvedValue({
                "shop-1": { name: "Shop 1", last_ping: NOW - 10 },
                "shop-2": { name: "Shop 2", last_ping: NOW - 120 },
                engraver: { name: "Engraver", last_ping: NOW - 3 * 3600 },
                broken: null
            }),
            listJobs: vi.fn().mockResolvedValue({
                a: { id: "a", status: "printing" },
                b: { id: "b", status: "queued" },
                c: { id: "c", status: "finished" },
                broken: null
            }),
            logout: vi.fn().mockResolvedValue(undefined)
        } as unknown as ColonyPrintAPI;
    });

    afterEach(() => {
        cleanup();
        localStorage.clear();
    });

    test("test_render", async () => {
        await renderBar("/nodes/shop-1");
        const nav = screen.getByRole("navigation", { name: "Main" });
        expect(nav.className).toBe("side-bar");
        expect(screen.getByRole("img", { name: "Colony Print" })).toBeTruthy();
        expect(screen.getByText("admin · server 0.25.0").className).toBe(
            "side-bar-session"
        );
        expect(
            Array.from(nav.querySelectorAll(".side-bar-group-label")).map(
                (label) => label.textContent
            )
        ).toEqual(["Monitor", "System"]);
        expect(
            screen
                .getAllByRole("link")
                .map((link) => [link.textContent, link.getAttribute("href")])
        ).toEqual([
            ["Dashboard", "/"],
            ["Nodes2/3", "/nodes"],
            ["Jobs2", "/jobs"],
            ["Printers", "/printers"],
            ["Settings", "/settings"]
        ]);
    });

    test("test_render_active", async () => {
        await renderBar("/nodes/shop-1");
        const nodes = screen.getByRole("link", { name: /^Nodes/ });
        expect(nodes.getAttribute("aria-current")).toBe("page");
        expect(nodes.className).toBe("link side-bar-link side-bar-link-active");
        expect(nodes.querySelector("ion-icon")?.getAttribute("icon")).toBe(
            serverOutline
        );

        // the other items, the dashboard included (its path being the
        // start of every path), are not active
        const dashboard = screen.getByRole("link", { name: "Dashboard" });
        expect(dashboard.getAttribute("aria-current")).toBe(null);
        expect(dashboard.className).toBe("link side-bar-link");
        const jobs = screen.getByRole("link", { name: /^Jobs/ });
        expect(jobs.querySelector("ion-icon")?.getAttribute("icon")).toBe(
            documentTextOutline
        );
        cleanup();

        await renderBar("/");
        expect(
            screen
                .getByRole("link", { name: "Dashboard" })
                .getAttribute("aria-current")
        ).toBe("page");
        expect(
            screen
                .getByRole("link", { name: /^Nodes/ })
                .getAttribute("aria-current")
        ).toBe(null);
    });

    test("test_render_open", async () => {
        await renderBar("/", { open: true });
        expect(screen.getByRole("navigation", { name: "Main" }).className).toBe(
            "side-bar side-bar-open"
        );
    });

    test("test_render_session", async () => {
        // without the info of the server (e.g., an expired session)
        // only the name of the user is shown, and nothing without both
        api.getInfo = vi.fn().mockRejectedValue(new Error("Forbidden"));
        const { container } = await renderBar("/");
        expect(container.querySelector(".side-bar-session")?.textContent).toBe(
            "admin"
        );
        cleanup();

        await renderBar("/", { username: null });
        expect(document.querySelector(".side-bar-session")).toBe(null);
    });

    test("test_badges", async () => {
        const { container } = await renderBar("/");
        const count = container.querySelector(".side-bar-count");
        expect(count?.textContent).toBe("2/3");
        expect(count?.getAttribute("title")).toBe("2 of 3 nodes online");
        const badge = container.querySelector(".side-bar-badge");
        expect(badge?.textContent).toBe("2");
        expect(badge?.getAttribute("title")).toBe("2 jobs in flight");
        expect(badge?.parentElement?.getAttribute("href")).toBe("/jobs");
    });

    test("test_badges_idle", async () => {
        // without jobs in flight there's no badge, as there's nothing
        // that requires the attention of the user
        api.listJobs = vi.fn().mockResolvedValue({
            c: { id: "c", status: "finished" }
        });
        const { container } = await renderBar("/");
        expect(container.querySelector(".side-bar-badge")).toBe(null);
        expect(container.querySelector(".side-bar-count")?.textContent).toBe(
            "2/3"
        );
    });

    test("test_badges_error", async () => {
        // the counts that can't be retrieved are not shown, instead
        // of being shown as zero
        api.listNodes = vi.fn().mockRejectedValue(new Error("Offline"));
        api.listJobs = vi.fn().mockRejectedValue(new Error("Offline"));
        const { container } = await renderBar("/");
        expect(container.querySelector(".side-bar-count")).toBe(null);
        expect(container.querySelector(".side-bar-badge")).toBe(null);
        expect(screen.getByRole("link", { name: "Nodes" })).toBeTruthy();
    });

    test("test_click", async () => {
        const onClose = vi.fn();
        await renderBar("/", { onClose: onClose });
        await act(async () => {
            fireEvent.click(screen.getByRole("link", { name: /^Jobs/ }));
        });
        expect(onClose).toHaveBeenCalledTimes(1);
        expect(location).toBe("/jobs");
    });

    test("test_click_refresh", async () => {
        // every navigation refreshes the status and the counts, so
        // that they follow the ones of the shown page
        await renderBar("/");
        expect(api.listJobs).toHaveBeenCalledTimes(1);
        api.listJobs = vi.fn().mockResolvedValue({});
        await act(async () => {
            fireEvent.click(screen.getByRole("link", { name: /^Jobs/ }));
        });
        expect(api.listJobs).toHaveBeenCalledTimes(1);
        expect(api.ping).toHaveBeenCalledTimes(2);
        expect(document.querySelector(".side-bar-badge")).toBe(null);
    });

    test("test_status", async () => {
        const { container } = await renderBar("/");
        expect(screen.getByText("API healthy")).toBeTruthy();
        expect(screen.getByText("up 6d 4h").className).toBe(
            "side-bar-status-uptime"
        );
        expect(container.querySelector(".side-bar-status-dot")?.className).toBe(
            "side-bar-status-dot side-bar-status-healthy"
        );
    });

    test("test_status_loading", () => {
        api.ping = vi.fn().mockReturnValue(new Promise(() => {}));
        const { container } = render(
            <APIContext.Provider value={api}>
                <MemoryRouter>
                    <SideBar />
                </MemoryRouter>
            </APIContext.Provider>
        );
        expect(screen.getByText("Connecting")).toBeTruthy();
        expect(container.querySelector(".side-bar-status-dot")?.className).toBe(
            "side-bar-status-dot side-bar-status-loading"
        );
        expect(container.querySelector(".side-bar-count")).toBe(null);
    });

    test("test_status_unreachable", async () => {
        api.ping = vi.fn().mockRejectedValue(new Error("Offline"));
        api.getInfo = vi.fn().mockRejectedValue(new Error("Offline"));
        const { container } = await renderBar("/");
        expect(screen.getByText("API unreachable")).toBeTruthy();
        expect(container.querySelector(".side-bar-status-uptime")).toBe(null);
        expect(container.querySelector(".side-bar-status-dot")?.className).toBe(
            "side-bar-status-dot side-bar-status-unreachable"
        );
    });

    test("test_status_session", async () => {
        // an expired session (whose info is refused) is not shown as
        // an unreachable server, as the health is the one of the ping
        api.getInfo = vi.fn().mockRejectedValue(new Error("Forbidden"));
        const { container } = await renderBar("/");
        expect(screen.getByText("API healthy")).toBeTruthy();
        expect(container.querySelector(".side-bar-status-uptime")).toBe(null);
    });

    test("test_status_uptime", async () => {
        api.getInfo = vi
            .fn()
            .mockResolvedValue({ version: "0.25.0", uptime: null });
        const { container } = await renderBar("/");
        expect(container.querySelector(".side-bar-status-uptime")).toBe(null);
        expect(screen.getByText("admin · server 0.25.0")).toBeTruthy();
    });

    test("test_logout", async () => {
        const { container } = await renderBar("/settings");
        expect(screen.getByText("admin").className).toBe("side-bar-user-name");
        const avatar = container.querySelector(".side-bar-avatar");
        expect(avatar?.textContent).toBe("AD");
        expect(avatar?.getAttribute("aria-hidden")).toBe("true");
        await act(async () => {
            fireEvent.click(screen.getByRole("button", { name: "Log out" }));
        });
        expect(api.logout).toHaveBeenCalledTimes(1);
        expect(location).toBe("/login");
    });

    test("test_logout_short", async () => {
        // the initials of a single letter name are that letter
        const { container } = await renderBar("/", { username: "j" });
        expect(container.querySelector(".side-bar-avatar")?.textContent).toBe(
            "J"
        );
    });

    test("test_logout_missing", async () => {
        const { container } = await renderBar("/", { username: null });
        expect(screen.queryByRole("button", { name: "Log out" })).toBe(null);
        expect(container.querySelector(".side-bar-avatar")).toBe(null);
    });
});
