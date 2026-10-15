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
import { logoTux, logoWindows } from "ionicons/icons";

import { ColonyPrintAPI, NodeInfo } from "../../../../api/colony-print";
import { APIContext } from "../../../../contexts";
import { NodesList } from "../../../../components/templates/nodes/nodes-list";

const NOW = Date.now() / 1000;

let search = "";

const MockLocation: FC = () => {
    search = useLocation().search;
    return null;
};

const mockNode = (values: Partial<NodeInfo>): NodeInfo =>
    ({
        name: "Node",
        location: "Porto",
        mode: "normal",
        printer: "default",
        engines: ["npcolony", "text"],
        platform: "win32",
        os: "nt",
        version: "0.25.0",
        last_ping: NOW - 10,
        ...values
    }) as NodeInfo;

describe("NodesListTest", () => {
    let api: ColonyPrintAPI;

    const renderList = async (path = "/nodes") => {
        const result = render(
            <APIContext.Provider value={api}>
                <MemoryRouter initialEntries={[path]}>
                    <NodesList />
                    <Routes>
                        <Route path="*" element={<MockLocation />} />
                    </Routes>
                </MemoryRouter>
            </APIContext.Provider>
        );
        await act(async () => {});
        return result;
    };

    const rows = (container: HTMLElement) =>
        Array.from(container.querySelectorAll("tbody tr"));

    const cells = (row: Element) =>
        Array.from(row.querySelectorAll("td")).map((cell) => cell.textContent);

    const footer = (container: HTMLElement) =>
        container.querySelector(".data-table-footer")?.textContent;

    beforeEach(() => {
        search = "";
        api = {
            listNodes: vi.fn().mockResolvedValue({
                "shop-1": mockNode({ name: "Shop 1" }),
                warehouse: mockNode({
                    name: "Warehouse",
                    platform: "linux",
                    os: "posix",
                    mode: "email",
                    engines: []
                }),
                engraver: mockNode({
                    name: "Engraver",
                    version: "0.24.0",
                    os: "java",
                    platform: "",
                    last_ping: NOW - 3 * 3600
                }),
                partial: { location: "Porto" },
                broken: null
            }),
            getInfo: vi.fn().mockResolvedValue({ version: "0.25.0" }),
            listJobs: vi.fn().mockResolvedValue({
                a: { id: "a", node_id: "shop-1" },
                b: { id: "b", node_id: "shop-1" },
                c: { id: "c", node_id: "engraver" },
                d: { id: "d", node_id: "other" },
                e: { id: "e", node_id: "shop-1", type: "restart" },
                f: { id: "f", node_id: "engraver", type: "auto-update" },
                broken: null
            })
        } as unknown as ColonyPrintAPI;
    });

    afterEach(() => {
        cleanup();
    });

    test("test_render", async () => {
        const { container } = await renderList();
        expect(
            Array.from(container.querySelectorAll("th")).map(
                (th) => th.textContent
            )
        ).toEqual([
            "State",
            "Node",
            "Location",
            "Mode",
            "Printer",
            "Platform",
            "Engines",
            "Version",
            "Jobs",
            "Last Seen"
        ]);
        expect(rows(container).map(cells)).toEqual([
            [
                "Online",
                "Shop 1 shop-1",
                "Porto",
                "normal",
                "default",
                "win32",
                "npcolony, text",
                "0.25.0",
                "2",
                "just now"
            ],
            [
                "Online",
                "Warehouse warehouse",
                "Porto",
                "email",
                "default",
                "linux",
                "-",
                "0.25.0",
                "0",
                "just now"
            ],
            [
                "Offline",
                "Engraver engraver",
                "Porto",
                "normal",
                "default",
                "-",
                "npcolony, text",
                "0.24.0",
                "1",
                "3h ago"
            ]
        ]);
        expect(
            screen
                .getByRole("link", { name: "Engraver engraver" })
                .getAttribute("href")
        ).toBe("/nodes/engraver");
        expect(
            Array.from(container.querySelectorAll("tbody .status")).map(
                (status) => status.className
            )
        ).toEqual([
            "status status-success",
            "status status-success",
            "status status-default"
        ]);
    });

    test("test_render_jobs", async () => {
        // the commands of the nodes (e.g., their restarts) are not
        // counted as their jobs, so that the count is the same as the
        // total jobs of the page of the node (its statistics)
        const { container } = await renderList();
        expect(
            rows(container).map((row) =>
                cells(row).slice(1, 2).concat(cells(row)[8])
            )
        ).toEqual([
            ["Shop 1 shop-1", "2"],
            ["Warehouse warehouse", "0"],
            ["Engraver engraver", "1"]
        ]);
    });

    test("test_render_missing", async () => {
        // the nodes of older versions report less, the missing fields
        // being shown as so (and the version not taken as behind)
        api.listNodes = vi.fn().mockResolvedValue({
            legacy: mockNode({
                name: "Legacy",
                location: "",
                printer: "",
                engines: undefined,
                version: ""
            } as unknown as Partial<NodeInfo>)
        });
        const { container } = await renderList();
        expect(cells(rows(container)[0])).toEqual([
            "Online",
            "Legacy legacy",
            "-",
            "normal",
            "-",
            "win32",
            "-",
            "-",
            "0",
            "just now"
        ]);
        expect(container.querySelector(".nodes-list-behind")).toBe(null);
    });

    test("test_render_platform", async () => {
        const { container } = await renderList();
        expect(
            rows(container).map((row) =>
                row
                    .querySelector(".nodes-list-platform ion-icon")
                    ?.getAttribute("icon")
            )
        ).toEqual([logoWindows, logoTux, undefined]);
    });

    test("test_render_version", async () => {
        const { container } = await renderList();

        // the versions behind the server are highlighted, as well as
        // the time since the offline nodes were last seen
        const behind = Array.from(
            container.querySelectorAll(".nodes-list-behind")
        );
        expect(behind.map((cell) => cell.textContent)).toEqual([
            "0.24.0",
            "3h ago"
        ]);
        expect(behind[0].getAttribute("title")).toBe(
            "Behind the server (0.25.0)"
        );
        expect(
            Array.from(container.querySelectorAll("td .tag-warning")).map(
                (tag) => tag.textContent
            )
        ).toEqual(["email"]);
        expect(footer(container)).toBe(
            "3 of 3 nodesVersion behind the server (0.25.0)"
        );
        expect(container.querySelector(".nodes-list-swatch")).toBeTruthy();
    });

    test("test_filter", async () => {
        const { container } = await renderList();
        const group = screen.getByRole("group", { name: "Filter by state" });
        expect(
            Array.from(group.querySelectorAll("button")).map(
                (button) => button.textContent
            )
        ).toEqual(["All3", "Online2", "Offline1"]);

        fireEvent.click(screen.getByRole("button", { name: "Online2" }));
        expect(rows(container).map((row) => cells(row)[1])).toEqual([
            "Shop 1 shop-1",
            "Warehouse warehouse"
        ]);
        expect(search).toBe("?state=online");
        expect(container.querySelector(".nodes-list-footer")?.textContent).toBe(
            "2 of 3 nodes"
        );

        fireEvent.click(screen.getByRole("button", { name: "Offline1" }));
        expect(rows(container).map((row) => cells(row)[1])).toEqual([
            "Engraver engraver"
        ]);
        expect(search).toBe("?state=offline");

        // the default filter is not kept in the address of the page
        fireEvent.click(screen.getByRole("button", { name: "All3" }));
        expect(rows(container).length).toBe(3);
        expect(search).toBe("");
    });

    test("test_filter_time", async () => {
        // a node that goes offline while the page is shown keeps the
        // state it was retrieved with, so that its counts, its filter
        // and its rows agree until the page is refreshed
        vi.useFakeTimers({ toFake: ["Date"] });
        vi.setSystemTime(NOW * 1000);
        try {
            api.listNodes = vi.fn().mockResolvedValue({
                edge: mockNode({ name: "Edge", last_ping: NOW - 890 })
            });
            const { container } = await renderList();
            vi.setSystemTime((NOW + 20) * 1000);
            fireEvent.click(screen.getByRole("button", { name: "Offline0" }));
            expect(rows(container).map(cells)).toEqual([
                ["No nodes registered"]
            ]);

            fireEvent.click(screen.getByRole("button", { name: "Online1" }));
            expect(rows(container).map((row) => cells(row)[0])).toEqual([
                "Online"
            ]);
        } finally {
            vi.useRealTimers();
        }
    });

    test("test_filter_address", async () => {
        // the filter is the one of the address of the page, so that
        // a refresh (or a link) keeps it
        const { container } = await renderList("/nodes?state=offline");
        expect(rows(container).map((row) => cells(row)[1])).toEqual([
            "Engraver engraver"
        ]);
        expect(
            screen
                .getByRole("button", { name: "Offline1" })
                .getAttribute("aria-pressed")
        ).toBe("true");
        cleanup();

        // while an unknown one is ignored, showing all of the nodes
        const other = await renderList("/nodes?state=unknown");
        expect(rows(other.container).length).toBe(3);
        expect(
            screen
                .getByRole("button", { name: "All3" })
                .getAttribute("aria-pressed")
        ).toBe("true");
    });

    test("test_render_error", async () => {
        api.listNodes = vi.fn().mockRejectedValue(new Error("Offline"));
        const { container } = await renderList();
        expect(screen.getByText("No nodes registered")).toBeTruthy();
        expect(container.querySelector(".nodes-list-footer")?.textContent).toBe(
            "0 of 0 nodes"
        );
    });

    test("test_render_info_error", async () => {
        // without the version of the server no node is behind it
        api.getInfo = vi.fn().mockRejectedValue(new Error("Forbidden"));
        const { container } = await renderList();
        expect(rows(container).length).toBe(3);
        expect(
            Array.from(container.querySelectorAll(".nodes-list-behind")).map(
                (cell) => cell.textContent
            )
        ).toEqual(["3h ago"]);
        expect(footer(container)).toBe("3 of 3 nodes");
        expect(container.querySelector(".nodes-list-legend")).toBe(null);
    });

    test("test_render_jobs_error", async () => {
        // the nodes are still listed when their jobs can't be, as
        // having no jobs
        api.listJobs = vi.fn().mockRejectedValue(new Error("Offline"));
        const { container } = await renderList();
        expect(rows(container).map((row) => cells(row)[8])).toEqual([
            "0",
            "0",
            "0"
        ]);
    });

    test("test_render_loading", () => {
        api.listNodes = vi.fn().mockReturnValue(new Promise(() => {}));
        const { container } = render(
            <APIContext.Provider value={api}>
                <MemoryRouter>
                    <NodesList />
                </MemoryRouter>
            </APIContext.Provider>
        );
        expect(container.querySelector(".loader")).toBeTruthy();
        expect(container.querySelector(".data-table-footer")).toBe(null);
    });
});
