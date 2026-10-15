import React from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import { act, cleanup, render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import {
    ColonyPrintAPI,
    JobInfo,
    NodeInfo
} from "../../../../api/colony-print";
import { APIContext } from "../../../../contexts";
import { Dashboard } from "../../../../components/templates/dashboard/dashboard";

const NOW = Date.now() / 1000;

const mockNode = (values: Partial<NodeInfo>): NodeInfo =>
    ({
        name: "Node",
        version: "0.25.0",
        last_ping: NOW - 10,
        ...values
    }) as NodeInfo;

const mockJob = (values: Partial<JobInfo>): JobInfo =>
    ({
        node_id: "shop-1",
        status: "queued",
        queued_time: NOW,
        ...values
    }) as JobInfo;

describe("DashboardTest", () => {
    let api: ColonyPrintAPI;

    const renderDashboard = async () => {
        const result = render(
            <APIContext.Provider value={api}>
                <MemoryRouter>
                    <Dashboard />
                </MemoryRouter>
            </APIContext.Provider>
        );
        await act(async () => {});
        return result;
    };

    const stat = (container: HTMLElement, label: string) => {
        const card = Array.from(container.querySelectorAll(".stat-card")).find(
            (card) =>
                card.querySelector(".stat-card-label")?.textContent === label
        );
        return [
            card?.querySelector(".stat-card-value")?.textContent,
            card?.querySelector(".stat-card-description")?.textContent
        ];
    };

    const panel = (name: string) =>
        screen
            .getByRole("heading", { name: name })
            .closest("section") as HTMLElement;

    beforeEach(() => {
        api = {
            listNodes: vi.fn().mockResolvedValue({
                "shop-1": mockNode({ name: "Shop 1" }),
                "shop-2": mockNode({ name: "Shop 2", last_ping: NOW - 120 }),
                engraver: mockNode({
                    name: "Engraver",
                    version: "0.24.0",
                    last_ping: NOW - 3 * 3600
                }),
                partial: { location: "Porto" },
                broken: null
            }),
            listJobs: vi.fn().mockResolvedValue({
                a: mockJob({
                    id: "a",
                    name: "FS 1",
                    status: "finished",
                    result: { result: "success" },
                    queued_time: NOW - 60
                }),
                b: mockJob({
                    id: "b",
                    name: "FS 2",
                    status: "finished",
                    result: { result: "error" },
                    queued_time: NOW - 30
                }),
                c: mockJob({ id: "c", name: "Label", status: "printing" }),
                d: mockJob({
                    id: "d",
                    status: "queued",
                    queued_time: NOW - 90
                }),
                e: mockJob({
                    id: "e",
                    name: "Old",
                    node_id: "",
                    status: "cancelled",
                    queued_time: NOW - 120
                })
            }),
            ping: vi.fn().mockResolvedValue({ time: NOW }),
            getInfo: vi.fn().mockResolvedValue({
                version: "0.25.0",
                uptime: 6 * 86400 + 4 * 3600
            })
        } as unknown as ColonyPrintAPI;
    });

    afterEach(() => {
        cleanup();
    });

    test("test_render", async () => {
        const { container } = await renderDashboard();
        expect(stat(container, "Nodes")).toEqual(["3", "2 online, 1 offline"]);
        expect(stat(container, "Jobs Tracked")).toEqual([
            "5",
            "1 ok, 1 failed"
        ]);
        expect(stat(container, "In Flight")).toEqual([
            "2",
            "1 printing, 1 queued"
        ]);
        expect(stat(container, "API")).toEqual(["Healthy", "0.25.0, up 6d 4h"]);
        expect(container.querySelectorAll(".stat-card ion-icon").length).toBe(
            4
        );
        expect(
            container.querySelector(".stat-card-value .status")?.className
        ).toBe("status status-success dashboard-health");

        // the online nodes and the failed jobs are highlighted
        expect(container.querySelector(".dashboard-success")?.textContent).toBe(
            "2 online"
        );
        expect(container.querySelector(".dashboard-error")?.textContent).toBe(
            "1 failed"
        );
    });

    test("test_render_updated", async () => {
        await renderDashboard();
        expect(
            screen.getByText(
                /^Overview of your Colony Print infrastructure, updated /
            )
        ).toBeTruthy();
    });

    test("test_render_highlights", async () => {
        // nothing is highlighted when there's nothing online, or
        // nothing failed, as zero is not a success nor an error
        api.listNodes = vi.fn().mockResolvedValue({
            engraver: mockNode({ name: "Engraver", last_ping: NOW - 3 * 3600 })
        });
        api.listJobs = vi.fn().mockResolvedValue({
            a: mockJob({
                id: "a",
                status: "finished",
                result: { result: "success" }
            })
        });
        const { container } = await renderDashboard();
        expect(stat(container, "Nodes")).toEqual(["1", "0 online, 1 offline"]);
        expect(stat(container, "Jobs Tracked")).toEqual([
            "1",
            "1 ok, 0 failed"
        ]);
        expect(container.querySelector(".dashboard-success")).toBe(null);
        expect(container.querySelector(".dashboard-error")).toBe(null);
    });

    test("test_render_distribution", async () => {
        const { container } = await renderDashboard();
        expect(screen.getByText("The 5 jobs kept by the server")).toBeTruthy();
        expect(
            Array.from(
                container.querySelectorAll(".distribution-bar-item")
            ).map((item) => item.textContent)
        ).toEqual([
            "Succeeded1",
            "Failed1",
            "Printing1",
            "Queued1",
            "Cancelled1"
        ]);
    });

    test("test_render_distribution_invalid", async () => {
        // the entries that are not jobs (without an identifier) are
        // left out of the jobs tracked, as they are of their counts
        api.listJobs = vi.fn().mockResolvedValue({
            a: mockJob({
                id: "a",
                status: "finished",
                result: { result: "success" }
            }),
            b: mockJob({ id: "b", status: "printing" }),
            partial: { name: "Partial" },
            broken: null
        });
        const { container } = await renderDashboard();
        expect(stat(container, "Jobs Tracked")).toEqual([
            "2",
            "1 ok, 0 failed"
        ]);
        expect(screen.getByText("The 2 jobs kept by the server")).toBeTruthy();
    });

    test("test_render_recent", async () => {
        const { container } = await renderDashboard();
        const recent = panel("Recent Jobs");
        expect(
            Array.from(recent.querySelectorAll("th")).map(
                (th) => th.textContent
            )
        ).toEqual(["Queued", "Job", "Node", "Status"]);
        const rows = Array.from(recent.querySelectorAll("tbody tr")).map(
            (row) =>
                Array.from(row.querySelectorAll("td")).map(
                    (cell) => cell.textContent
                )
        );
        expect(rows).toEqual([
            ["just now", "Label", "shop-1", "Printing"],
            ["just now", "FS 2", "shop-1", "Failed"],
            ["1m ago", "FS 1", "shop-1", "Finished"],
            ["1m ago", "d", "shop-1", "Queued"],
            ["2m ago", "Old", "-", "Cancelled"]
        ]);
        expect(
            Array.from(recent.querySelectorAll("tbody .status")).map(
                (status) => status.className
            )
        ).toEqual([
            "status status-warning",
            "status status-error",
            "status status-success",
            "status status-info",
            "status status-default"
        ]);
        expect(
            screen.getByRole("link", { name: "FS 2" }).getAttribute("href")
        ).toBe("/jobs/b");
        expect(
            recent.querySelector(".panel-header a")?.getAttribute("href")
        ).toBe("/jobs");
        expect(
            recent.querySelector(".dashboard-time")?.getAttribute("title")
        ).toBe(new Date(NOW * 1000).toLocaleString());
        expect(container.querySelectorAll(".dashboard-panel").length).toBe(2);
    });

    test("test_render_recent_limit", async () => {
        const jobs: Record<string, JobInfo> = {};
        for (let index = 0; index < 12; index++) {
            jobs[`j${index}`] = mockJob({
                id: `j${index}`,
                name: `Job ${index}`,
                queued_time: NOW - index
            });
        }
        api.listJobs = vi.fn().mockResolvedValue(jobs);
        await renderDashboard();
        const rows = Array.from(
            panel("Recent Jobs").querySelectorAll("tbody tr")
        );
        expect(rows.length).toBe(10);
        expect(rows[0].querySelectorAll("td")[1].textContent).toBe("Job 0");
        expect(rows[9].querySelectorAll("td")[1].textContent).toBe("Job 9");
    });

    test("test_render_nodes", async () => {
        await renderDashboard();
        const nodes = panel("Node Status");
        const rows = Array.from(nodes.querySelectorAll(".dashboard-node"));
        expect(
            rows.map((row) => [
                row.querySelector(".status")?.getAttribute("aria-label"),
                row.querySelector(".dashboard-node-name")?.textContent,
                row.querySelector(".tag, .dashboard-node-version")?.textContent,
                row.querySelector(".dashboard-node-seen")?.textContent
            ])
        ).toEqual([
            ["Online", "Shop 1 shop-1", "0.25.0", "just now"],
            ["Online", "Shop 2 shop-2", "0.25.0", "2m ago"],
            ["Offline", "Engraver engraver", "0.24.0", "3h ago"]
        ]);
        expect(
            screen.getByRole("link", { name: /^Offline Engraver engraver/ })
        ).toBeTruthy();
        expect(rows.map((row) => row.getAttribute("href"))).toEqual([
            "/nodes/shop-1",
            "/nodes/shop-2",
            "/nodes/engraver"
        ]);

        // the versions behind the server are highlighted, as well as
        // the time since the offline nodes were last seen
        expect(nodes.querySelector(".tag-warning")?.textContent).toBe("0.24.0");
        expect(
            Array.from(nodes.querySelectorAll(".dashboard-node-offline")).map(
                (seen) => seen.textContent
            )
        ).toEqual(["3h ago"]);
        expect(
            nodes.querySelector(".panel-header a")?.getAttribute("href")
        ).toBe("/nodes");
    });

    test("test_render_nodes_version", async () => {
        // the nodes that don't report their version are shown without
        // it, and are not taken as behind the server
        api.listNodes = vi.fn().mockResolvedValue({
            legacy: mockNode({ name: "Legacy", version: "" })
        });
        await renderDashboard();
        const nodes = panel("Node Status");
        expect(
            nodes.querySelector(".dashboard-node-version")?.textContent
        ).toBe("-");
        expect(nodes.querySelector(".tag-warning")).toBe(null);
    });

    test("test_render_loading", () => {
        api.listNodes = vi.fn().mockReturnValue(new Promise(() => {}));
        const { container } = render(
            <APIContext.Provider value={api}>
                <MemoryRouter>
                    <Dashboard />
                </MemoryRouter>
            </APIContext.Provider>
        );
        expect(stat(container, "Nodes")).toEqual([
            "-",
            "Registered print nodes"
        ]);
        expect(stat(container, "Jobs Tracked")).toEqual([
            "-",
            "Total tracked jobs"
        ]);
        expect(stat(container, "API")).toEqual(["-", "API server status"]);
        expect(container.querySelectorAll(".loader").length).toBe(2);
        expect(
            screen.getByText("Overview of your Colony Print infrastructure")
        ).toBeTruthy();
    });

    test("test_render_unreachable", async () => {
        api.listNodes = vi.fn().mockRejectedValue(new Error("Offline"));
        api.listJobs = vi.fn().mockRejectedValue(new Error("Offline"));
        api.ping = vi.fn().mockRejectedValue(new Error("Offline"));
        api.getInfo = vi.fn().mockRejectedValue(new Error("Offline"));
        const { container } = await renderDashboard();
        expect(stat(container, "Nodes")).toEqual(["0", "0 online, 0 offline"]);
        expect(stat(container, "API")).toEqual([
            "Unreachable",
            "API server status"
        ]);
        expect(
            container.querySelector(".stat-card-value .status")?.className
        ).toBe("status status-error dashboard-health");
        expect(screen.getByText("No recent jobs")).toBeTruthy();
        expect(screen.getByText("No nodes registered")).toBeTruthy();
        expect(
            container.querySelectorAll(".distribution-bar-segment").length
        ).toBe(0);
    });

    test("test_render_session", async () => {
        // without the info (e.g., an expired session) the server is
        // still healthy, with no version to compare the nodes with
        api.getInfo = vi.fn().mockRejectedValue(new Error("Forbidden"));
        const { container } = await renderDashboard();
        expect(stat(container, "API")).toEqual([
            "Healthy",
            "API server status"
        ]);
        expect(panel("Node Status").querySelector(".tag-warning")).toBe(null);
    });

    test("test_render_uptime", async () => {
        api.getInfo = vi
            .fn()
            .mockResolvedValue({ version: "0.25.0", uptime: null });
        const { container } = await renderDashboard();
        expect(stat(container, "API")).toEqual(["Healthy", "0.25.0"]);
    });
});
