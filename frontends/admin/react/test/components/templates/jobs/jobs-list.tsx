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
import {
    cloudDownloadOutline,
    diamondOutline,
    printOutline
} from "ionicons/icons";

import { ColonyPrintAPI, JobInfo } from "../../../../api/colony-print";
import { APIContext } from "../../../../contexts";
import { JobsList } from "../../../../components/templates/jobs/jobs-list";

const NOW = Date.now() / 1000;

let search = "";

const MockLocation: FC = () => {
    search = useLocation().search;
    return null;
};

const mockJob = (values: Partial<JobInfo>): JobInfo =>
    ({
        node_id: "shop-1",
        status: "queued",
        type: "npcolony",
        format: "binie",
        queued_time: NOW,
        ...values
    }) as JobInfo;

describe("JobsListTest", () => {
    let api: ColonyPrintAPI;

    const renderList = async (path = "/jobs") => {
        const result = render(
            <APIContext.Provider value={api}>
                <MemoryRouter initialEntries={[path]}>
                    <JobsList />
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
        container.querySelector(".jobs-list-footer")?.textContent;

    const filter = (query: string) =>
        fireEvent.change(
            screen.getByRole("searchbox", { name: "Filter jobs" }),
            {
                target: { value: query }
            }
        );

    beforeEach(() => {
        search = "";
        api = {
            listJobs: vi.fn().mockResolvedValue({
                "4f1c9a2e7d": mockJob({
                    id: "4f1c9a2e7d",
                    name: "FS 2026/1043",
                    status: "finished",
                    result: { result: "success" },
                    queued_time: NOW - 60,
                    finish_time: NOW - 58
                }),
                b7e30d51aa: mockJob({
                    id: "b7e30d51aa",
                    name: "Label 560",
                    node_id: "shop-2",
                    status: "printing",
                    format: "xmpl",
                    queued_time: NOW - 30
                }),
                "0d92f6c4bb": mockJob({
                    id: "0d92f6c4bb",
                    name: "Signature plate",
                    node_id: "engraver",
                    type: "gravo",
                    format: undefined,
                    queued_time: NOW - 90
                }),
                "71d4a8f0ee": mockJob({
                    id: "71d4a8f0ee",
                    name: "update",
                    node_id: "warehouse",
                    status: "finished",
                    type: "update",
                    format: undefined,
                    result: {
                        result: "success",
                        before: { version: "0.24.0" },
                        after: { version: "0.25.0" }
                    },
                    queued_time: NOW - 120,
                    finish_time: NOW - 100
                }),
                e3c0478bdd: mockJob({
                    id: "e3c0478bdd",
                    name: "",
                    node_id: "",
                    status: "cancelled",
                    type: "custom",
                    result: { result: "error" },
                    queued_time: NOW - 150
                }),
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
            "Queued",
            "ID",
            "Name",
            "Node",
            "Type",
            "Format",
            "Status",
            "Result",
            "Finished"
        ]);
        const time = (timestamp: number) =>
            new Date(timestamp * 1000).toLocaleTimeString();
        expect(rows(container).map(cells)).toEqual([
            [
                time(NOW - 30),
                "b7e30d51",
                "Label 560",
                "shop-2",
                "npcolony",
                "xmpl",
                "Printing",
                "-",
                "-"
            ],
            [
                time(NOW - 60),
                "4f1c9a2e",
                "FS 2026/1043",
                "shop-1",
                "npcolony",
                "binie",
                "Finished",
                "success",
                time(NOW - 58)
            ],
            [
                time(NOW - 90),
                "0d92f6c4",
                "Signature plate",
                "engraver",
                "gravo",
                "-",
                "Queued",
                "-",
                "-"
            ],
            [
                time(NOW - 120),
                "71d4a8f0",
                "update",
                "warehouse",
                "update",
                "-",
                "Finished",
                "success0.24.0 → 0.25.0",
                time(NOW - 100)
            ],
            [
                time(NOW - 150),
                "e3c0478b",
                "-",
                "-",
                "custom",
                "binie",
                "Cancelled",
                "error",
                "-"
            ]
        ]);
        expect(footer(container)).toBe("5 of 5 jobs");
    });

    test("test_render_links", async () => {
        await renderList();
        expect(
            screen.getByRole("link", { name: "4f1c9a2e" }).getAttribute("href")
        ).toBe("/jobs/4f1c9a2e7d");
        expect(
            screen.getByRole("link", { name: "engraver" }).getAttribute("href")
        ).toBe("/nodes/engraver");
    });

    test("test_render_details", async () => {
        const { container } = await renderList();
        expect(
            Array.from(container.querySelectorAll("tbody .status")).map(
                (status) => status.className
            )
        ).toEqual([
            "status status-warning",
            "status status-success",
            "status status-info",
            "status status-success",
            "status status-default"
        ]);
        expect(
            Array.from(
                container.querySelectorAll(".jobs-list-result > span")
            ).map((result) => [result.className, result.textContent])
        ).toEqual([
            ["jobs-list-result-success", "success"],
            ["jobs-list-result-success", "success"],
            ["jobs-list-versions", "0.24.0 → 0.25.0"],
            ["jobs-list-result-error", "error"]
        ]);

        // the types are shown with their icons, if known
        expect(
            rows(container).map((row) =>
                row
                    .querySelector(".jobs-list-type ion-icon")
                    ?.getAttribute("icon")
            )
        ).toEqual([
            printOutline,
            printOutline,
            diamondOutline,
            cloudDownloadOutline,
            undefined
        ]);

        // with the full time of the job on hover, as only its time of
        // day is shown for the jobs of today
        expect(
            container.querySelector(".jobs-list-time")?.getAttribute("title")
        ).toBe(new Date((NOW - 30) * 1000).toLocaleString());
    });

    test("test_render_type", async () => {
        api.listJobs = vi.fn().mockResolvedValue({
            a: mockJob({ id: "a", type: undefined })
        });
        const { container } = await renderList();
        expect(cells(rows(container)[0])[4]).toBe("-");
    });

    test("test_filter", async () => {
        const { container } = await renderList();
        const group = screen.getByRole("group", { name: "Filter by status" });
        expect(group.className).toBe("filter-tabs filter-tabs-underline");
        expect(
            Array.from(group.querySelectorAll("button")).map(
                (button) => button.textContent
            )
        ).toEqual(["All5", "Queued1", "Printing1", "Finished2", "Cancelled1"]);

        fireEvent.click(screen.getByRole("button", { name: "Finished2" }));
        expect(rows(container).map((row) => cells(row)[1])).toEqual([
            "4f1c9a2e",
            "71d4a8f0"
        ]);
        expect(search).toBe("?status=finished");
        expect(footer(container)).toBe("2 of 5 jobs");

        fireEvent.click(screen.getByRole("button", { name: "All5" }));
        expect(rows(container).length).toBe(5);
        expect(search).toBe("");
    });

    test("test_filter_query", async () => {
        const { container } = await renderList();

        // the query matches the identifier, the name and the node of
        // the jobs, regardless of their case
        filter("SHOP");
        expect(rows(container).map((row) => cells(row)[1])).toEqual([
            "b7e30d51",
            "4f1c9a2e"
        ]);
        expect(search).toBe("?query=SHOP");

        filter("0d92");
        expect(rows(container).map((row) => cells(row)[1])).toEqual([
            "0d92f6c4"
        ]);

        filter("plate");
        expect(rows(container).map((row) => cells(row)[1])).toEqual([
            "0d92f6c4"
        ]);

        // and is combined with the filter of the status, both being
        // kept in the address of the page
        filter("shop");
        fireEvent.click(screen.getByRole("button", { name: "Finished2" }));
        expect(rows(container).map((row) => cells(row)[1])).toEqual([
            "4f1c9a2e"
        ]);
        expect(search).toBe("?status=finished&query=shop");

        filter("nothing");
        expect(screen.getByText("No jobs found")).toBeTruthy();
        expect(footer(container)).toBe("0 of 5 jobs");

        filter("   ");
        expect(rows(container).length).toBe(2);
        filter("");
        expect(search).toBe("?status=finished");
    });

    test("test_filter_address", async () => {
        // the filters are the ones of the address of the page, so
        // that a refresh (or a link) keeps them
        const { container } = await renderList(
            "/jobs?status=finished&query=update"
        );
        expect(rows(container).map((row) => cells(row)[1])).toEqual([
            "71d4a8f0"
        ]);
        expect(
            (
                screen.getByRole("searchbox", {
                    name: "Filter jobs"
                }) as HTMLInputElement
            ).value
        ).toBe("update");
        cleanup();

        // while an unknown status is ignored, showing all of the jobs
        const other = await renderList("/jobs?status=unknown");
        expect(rows(other.container).length).toBe(5);
    });

    test("test_render_error", async () => {
        api.listJobs = vi.fn().mockRejectedValue(new Error("Offline"));
        const { container } = await renderList();
        expect(screen.getByText("No jobs found")).toBeTruthy();
        expect(footer(container)).toBe("0 of 0 jobs");
    });

    test("test_render_loading", () => {
        api.listJobs = vi.fn().mockReturnValue(new Promise(() => {}));
        const { container } = render(
            <APIContext.Provider value={api}>
                <MemoryRouter>
                    <JobsList />
                </MemoryRouter>
            </APIContext.Provider>
        );

        // the filters are kept while loading, the rows are not
        expect(container.querySelector(".loader")).toBeTruthy();
        expect(
            screen.getByRole("group", { name: "Filter by status" })
        ).toBeTruthy();
        expect(container.querySelector(".data-table-footer")).toBe(null);
    });
});
