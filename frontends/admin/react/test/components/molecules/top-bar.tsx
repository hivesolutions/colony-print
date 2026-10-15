import React from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { ColonyPrintAPI } from "../../../api/colony-print";
import { APIContext } from "../../../contexts";
import { TopBar } from "../../../components/molecules";

describe("TopBarTest", () => {
    let api: ColonyPrintAPI;

    const renderBar = (
        path: string,
        onToggleSidebar?: () => void,
        onRefresh?: () => void
    ) =>
        render(
            <APIContext.Provider value={api}>
                <MemoryRouter initialEntries={[path]}>
                    <TopBar
                        onToggleSidebar={onToggleSidebar}
                        onRefresh={onRefresh}
                    />
                </MemoryRouter>
            </APIContext.Provider>
        );

    beforeEach(() => {
        api = {
            listNodes: vi.fn().mockResolvedValue({}),
            listJobs: vi.fn().mockResolvedValue({})
        } as unknown as ColonyPrintAPI;
    });

    afterEach(() => {
        cleanup();
    });

    test("test_render", () => {
        renderBar("/nodes/shop-1");
        const breadcrumb = screen.getByRole("navigation", {
            name: "Breadcrumb"
        });
        expect(breadcrumb.textContent).toBe("Colony PrintNodesshop-1");
        const link = screen.getByRole("link", { name: "Nodes" });
        expect(link.getAttribute("href")).toBe("/nodes");
        const current = screen.getByText("shop-1");
        expect(current.getAttribute("aria-current")).toBe("page");
        expect(current.tagName).toBe("SPAN");
        expect(screen.getByRole("search")).toBeTruthy();
    });

    test("test_render_section", () => {
        renderBar("/jobs");
        expect(screen.queryByRole("link")).toBe(null);
        expect(screen.getByText("Jobs").getAttribute("aria-current")).toBe(
            "page"
        );
    });

    test("test_render_dashboard", () => {
        renderBar("/");
        expect(
            screen.getByRole("navigation", { name: "Breadcrumb" }).textContent
        ).toBe("Colony PrintDashboard");
    });

    test("test_toggle", () => {
        const onToggleSidebar = vi.fn();
        renderBar("/", onToggleSidebar);
        fireEvent.click(screen.getByRole("button", { name: "Toggle menu" }));
        expect(onToggleSidebar).toHaveBeenCalledTimes(1);
    });

    test("test_toggle_missing", () => {
        renderBar("/");
        expect(screen.queryByRole("button", { name: "Toggle menu" })).toBe(
            null
        );
    });

    test("test_refresh", () => {
        const onRefresh = vi.fn();
        renderBar("/", undefined, onRefresh);
        const button = screen.getByRole("button", { name: "Refresh" });
        expect(button.getAttribute("type")).toBe("button");
        expect(button.parentElement?.className).toBe("top-bar-actions");
        expect(button.previousElementSibling?.getAttribute("role")).toBe(
            "search"
        );
        fireEvent.click(button);
        expect(onRefresh).toHaveBeenCalledTimes(1);
    });

    test("test_refresh_missing", () => {
        renderBar("/");
        expect(screen.queryByRole("button", { name: "Refresh" })).toBe(null);
    });
});
