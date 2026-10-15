import React from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import {
    act,
    cleanup,
    fireEvent,
    render,
    screen,
    within
} from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { ColonyPrintAPI, NodePrinterInfo } from "../../../../api/colony-print";
import { APIContext } from "../../../../contexts";
import { PrintersList } from "../../../../components/templates/printers/printers-list";

const NOW = Date.now() / 1000;

const mockPrinter = (values: Partial<NodePrinterInfo>): NodePrinterInfo => ({
    name: "Receipt",
    engine: "npcolony",
    node_id: "shop-1",
    node_name: "Shop 1",
    last_ping: NOW - 10,
    is_default: false,
    media: "RP80x297",
    width: 226.77,
    length: 841.89,
    ...values
});

describe("PrintersListTest", () => {
    let api: ColonyPrintAPI;

    const renderList = async () => {
        const result = render(
            <APIContext.Provider value={api}>
                <MemoryRouter>
                    <PrintersList />
                </MemoryRouter>
            </APIContext.Provider>
        );
        await act(async () => {});
        return result;
    };

    const table = (name: string) =>
        screen
            .getByRole("heading", { name: name })
            .closest(".data-table-card") as HTMLElement;

    const rows = (element: HTMLElement) =>
        Array.from(element.querySelectorAll("tbody tr")).map((row) =>
            Array.from(row.querySelectorAll("td")).map(
                (cell) => cell.textContent
            )
        );

    beforeEach(() => {
        api = {
            listNodePrinters: vi.fn().mockResolvedValue([
                mockPrinter({ is_default: true }),
                mockPrinter({
                    name: "Microsoft Print to PDF",
                    media: "A4",
                    width: 595.28,
                    length: 841.89
                }),
                mockPrinter({
                    name: "Gravo engraver",
                    engine: "gravo",
                    node_id: "engraver",
                    node_name: "Engraver",
                    last_ping: NOW - 3 * 3600,
                    is_default: undefined,
                    media: undefined,
                    width: undefined,
                    length: undefined
                }),
                mockPrinter({
                    name: "office",
                    node_id: "warehouse",
                    node_name: null,
                    last_ping: null,
                    media: "A4",
                    width: 595.28,
                    length: 841.89
                })
            ]),
            listPrinters: vi.fn().mockResolvedValue([
                {
                    name: "Server PDF",
                    is_default: true,
                    media: "A4",
                    width: 595.28,
                    length: 841.89
                }
            ]),
            printNodeHello: vi.fn().mockResolvedValue({ id: "job" })
        } as unknown as ColonyPrintAPI;
    });

    afterEach(() => {
        cleanup();
    });

    test("test_render", async () => {
        await renderList();
        const nodes = table("Nodes");
        expect(
            Array.from(nodes.querySelectorAll("th")).map((th) => th.textContent)
        ).toEqual(["Printer", "Node", "Engine", "Media", "Paper", "Test"]);
        expect(rows(nodes)).toEqual([
            [
                "Receiptdefault",
                " Shop 1 shop-1",
                "npcolony",
                "RP80x297",
                "80 × 297 mm",
                "Test page"
            ],
            [
                "Microsoft Print to PDF",
                " Shop 1 shop-1",
                "npcolony",
                "A4",
                "210 × 297 mm",
                "Test page"
            ],
            [
                "Gravo engraver",
                " Engraver engraver",
                "gravo",
                "-",
                "-",
                "No test page"
            ],
            [
                "office",
                " warehouse warehouse",
                "npcolony",
                "A4",
                "210 × 297 mm",
                "Node offline"
            ]
        ]);

        // the counts of the printers and the nodes (and of the ones of
        // them that are offline) are shown with the printers
        expect(nodes.querySelector(".panel-actions")?.textContent).toBe("4");
        expect(nodes.querySelector(".data-table-footer")?.textContent).toBe(
            "4 printers on 3 nodes, 2 of them offline"
        );
        // the state of the node is part of the name of its link, as the
        // dot is all that shows it
        expect(
            screen
                .getAllByRole("link", { name: "Online Shop 1 shop-1" })[0]
                .getAttribute("href")
        ).toBe("/nodes/shop-1");
        expect(
            screen.getByRole("link", { name: "Offline warehouse warehouse" })
        ).toBeTruthy();
        expect(
            Array.from(nodes.querySelectorAll("tbody .status")).map((status) =>
                status.getAttribute("aria-label")
            )
        ).toEqual(["Online", "Online", "Offline", "Offline"]);
    });

    test("test_render_paper", async () => {
        // the paper is shown in millimeters, with its size in points (as
        // reported) on hover, when the printer reports it
        await renderList();
        const papers = Array.from(
            table("Nodes").querySelectorAll("td[data-label=Paper] span")
        );
        expect(papers.map((paper) => paper.getAttribute("title"))).toEqual([
            "226.77 × 841.89 pt",
            "595.28 × 841.89 pt",
            null,
            "595.28 × 841.89 pt"
        ]);
    });

    test("test_render_default", async () => {
        // the printer named by the node is the one tagged as its default
        // (the one of its jobs that select none) rather than the default
        // of the system, that is only tagged for the nodes that name none
        api.listNodePrinters = vi.fn().mockResolvedValue([
            mockPrinter({ node_printer: "OFFICE", is_default: true }),
            mockPrinter({ name: "office", node_printer: "OFFICE" }),
            mockPrinter({
                node_id: "warehouse",
                node_printer: "default",
                is_default: true
            }),
            mockPrinter({ name: "office", node_id: "warehouse" })
        ]);
        await renderList();
        expect(rows(table("Nodes")).map((row) => row[0])).toEqual([
            "Receipt",
            "officedefault",
            "Receiptdefault",
            "office"
        ]);
    });

    test("test_render_test", async () => {
        // the test page is only printed by npcolony, and is not offered
        // for the printers of the offline nodes, as it would wait for them
        await renderList();
        expect(screen.getByText("No test page").getAttribute("title")).toBe(
            "Test pages are printed by npcolony, not by gravo"
        );
        expect(screen.getByText("Node offline").getAttribute("title")).toBe(
            "The node is offline, its test page would wait for it"
        );
        expect(
            screen.getAllByRole("button", { name: "Test page" }).length
        ).toBe(2);
    });

    test("test_render_server", async () => {
        await renderList();
        const server = table("Server");
        expect(
            Array.from(server.querySelectorAll("th")).map(
                (th) => th.textContent
            )
        ).toEqual(["Printer", "Media", "Paper"]);
        expect(rows(server)).toEqual([
            ["Server PDFdefault", "A4", "210 × 297 mm"]
        ]);
        expect(server.querySelector(".panel-actions")?.textContent).toBe("1");
        expect(server.querySelector(".data-table-footer")).toBe(null);
    });

    test("test_print_test", async () => {
        let resolve: (value: unknown) => void = () => {};
        api.printNodeHello = vi
            .fn()
            .mockReturnValue(new Promise((r) => (resolve = r)));
        await renderList();
        const row = table("Nodes").querySelectorAll(
            "tbody tr"
        )[1] as HTMLElement;
        const button = within(row).getByRole("button", { name: "Test page" });
        fireEvent.click(button);
        expect(api.printNodeHello).toHaveBeenCalledWith(
            "shop-1",
            "Microsoft Print to PDF"
        );

        // the test page can't be sent twice while it's being queued
        expect((button as HTMLButtonElement).disabled).toBe(true);
        await act(async () => {
            resolve({ id: "job" });
        });
        expect(row.querySelector("td:last-child")?.textContent).toBe(
            "Test page queued"
        );
        expect(row.querySelector("td:last-child .status")?.className).toBe(
            "status status-info"
        );

        // while the other printers keep their own state
        expect(
            within(
                table("Nodes").querySelectorAll("tbody tr")[0] as HTMLElement
            ).getByRole("button", { name: "Test page" })
        ).toBeTruthy();
    });

    test("test_print_test_error", async () => {
        api.printNodeHello = vi
            .fn()
            .mockRejectedValueOnce(new Error("Offline"))
            .mockResolvedValue({ id: "job" });
        await renderList();
        const row = table("Nodes").querySelectorAll(
            "tbody tr"
        )[0] as HTMLElement;
        await act(async () => {
            fireEvent.click(
                within(row).getByRole("button", { name: "Test page" })
            );
        });

        // a test page that couldn't be queued is shown as failed, and can
        // be sent again
        expect(row.querySelector("td:last-child .status")?.textContent).toBe(
            "Failed"
        );
        const button = within(row).getByRole("button", { name: "Test page" });
        expect((button as HTMLButtonElement).disabled).toBe(false);
        await act(async () => {
            fireEvent.click(button);
        });
        expect(api.printNodeHello).toHaveBeenCalledTimes(2);
        expect(row.querySelector("td:last-child")?.textContent).toBe(
            "Test page queued"
        );
    });

    test("test_render_error", async () => {
        api.listNodePrinters = vi.fn().mockRejectedValue(new Error("Offline"));
        api.listPrinters = vi.fn().mockRejectedValue(new Error("Offline"));
        await renderList();
        expect(
            screen.getByText("No printers reported by the nodes")
        ).toBeTruthy();
        expect(screen.getByText("No printers on the server")).toBeTruthy();
        expect(
            table("Nodes").querySelector(".data-table-footer")?.textContent
        ).toBe("0 printers on 0 nodes");
    });

    test("test_render_loading", () => {
        api.listNodePrinters = vi.fn().mockReturnValue(new Promise(() => {}));
        const { container } = render(
            <APIContext.Provider value={api}>
                <MemoryRouter>
                    <PrintersList />
                </MemoryRouter>
            </APIContext.Provider>
        );
        expect(container.querySelectorAll(".loader").length).toBe(2);
        expect(screen.getByRole("heading", { name: "Nodes" })).toBeTruthy();
        expect(container.querySelector(".data-table-footer")).toBe(null);
    });
});
