import React from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import {
    act,
    cleanup,
    fireEvent,
    render,
    screen
} from "@testing-library/react";

import { App } from "../app";

const NOW = Date.now() / 1000;

const ROUTES: Record<string, unknown> = {
    "/nodes": {
        "shop-1": { name: "Shop 1", version: "0.25.0", last_ping: NOW - 10 }
    },
    "/jobs": {
        a: { id: "a", name: "FS 1", node_id: "shop-1", status: "finished" },
        b: { id: "b", name: "FS 2", node_id: "shop-1", status: "queued" }
    },
    "/ping": { time: NOW },
    "/info": { version: "0.25.0", uptime: 3600 }
};

describe("AppTest", () => {
    let fetch: ReturnType<typeof vi.fn>;

    const renderApp = async (path = "/") => {
        window.history.pushState({}, "", path);
        const result = render(<App />);
        await act(async () => {});
        return result;
    };

    const calls = (path: string) =>
        fetch.mock.calls.filter(
            ([url]) => new URL(url, "http://localhost").pathname === path
        ).length;

    beforeEach(() => {
        localStorage.setItem("sessionId", "sid");
        localStorage.setItem("username", "admin");
        fetch = vi.fn(async (url: string) => {
            const path = new URL(url, "http://localhost").pathname;
            if (path in ROUTES) {
                return new Response(JSON.stringify(ROUTES[path]), {
                    status: 200
                });
            }
            return new Response("Not found", { status: 404 });
        });
        vi.stubGlobal("fetch", fetch);
    });

    afterEach(() => {
        cleanup();
        localStorage.clear();
        vi.unstubAllGlobals();
    });

    test("test_render", async () => {
        const { container } = await renderApp();
        expect(screen.getByRole("navigation", { name: "Main" })).toBeTruthy();
        expect(
            screen.getByRole("navigation", { name: "Breadcrumb" }).textContent
        ).toBe("Colony PrintDashboard");
        expect(screen.getByRole("heading", { name: "Dashboard" })).toBeTruthy();
        expect(container.querySelector(".layout-body .content")).toBeTruthy();
        expect(container.querySelector(".layout-overlay")).toBe(null);

        // the session is sent with the requests of the pages
        const [, options] = fetch.mock.calls[0];
        expect(options.headers["X-Session-Id"]).toBe("sid");
    });

    test("test_render_login", async () => {
        // without a session the pages redirect to the login
        localStorage.clear();
        await renderApp("/nodes");
        expect(window.location.pathname).toBe("/login");
        expect(screen.getByRole("button", { name: "Sign in" })).toBeTruthy();
        expect(screen.queryByRole("navigation", { name: "Main" })).toBe(null);
    });

    test("test_render_unknown", async () => {
        await renderApp("/unknown");
        expect(window.location.pathname).toBe("/");
        expect(screen.getByRole("heading", { name: "Dashboard" })).toBeTruthy();
    });

    test("test_render_base", async () => {
        // the admin may be served under its own path by the server
        await renderApp("/admin-ui/jobs");
        expect(screen.getByRole("heading", { name: "Jobs" })).toBeTruthy();
        expect(
            screen.getByRole("link", { name: "Dashboard" }).getAttribute("href")
        ).toBe("/admin-ui");
    });

    test("test_toggle", async () => {
        const { container } = await renderApp();
        const nav = screen.getByRole("navigation", { name: "Main" });
        fireEvent.click(screen.getByRole("button", { name: "Toggle menu" }));
        expect(nav.className).toBe("side-bar side-bar-open");

        // the overlay closes the side bar, as does the navigation
        fireEvent.click(container.querySelector(".layout-overlay")!);
        expect(nav.className).toBe("side-bar");
        expect(container.querySelector(".layout-overlay")).toBe(null);

        fireEvent.click(screen.getByRole("button", { name: "Toggle menu" }));
        await act(async () => {
            fireEvent.click(screen.getByRole("link", { name: /^Jobs/ }));
        });
        expect(screen.getByRole("navigation", { name: "Main" }).className).toBe(
            "side-bar"
        );
        expect(window.location.pathname).toBe("/jobs");
    });

    test("test_refresh", async () => {
        await renderApp("/jobs?status=finished");
        expect(calls("/jobs")).toBe(2);
        expect(calls("/ping")).toBe(1);
        await act(async () => {
            fireEvent.click(screen.getByRole("button", { name: "Refresh" }));
        });

        // both the page and the side bar fetch their data again, the
        // filters of the page being kept on the way
        expect(calls("/jobs")).toBe(4);
        expect(calls("/ping")).toBe(2);
        expect(window.location.search).toBe("?status=finished");
        expect(
            screen
                .getByRole("button", { name: "Finished1" })
                .getAttribute("aria-pressed")
        ).toBe("true");
        expect(document.querySelectorAll("tbody tr").length).toBe(1);
    });
});
