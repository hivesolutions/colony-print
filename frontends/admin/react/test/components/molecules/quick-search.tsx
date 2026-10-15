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

import { ColonyPrintAPI } from "../../../api/colony-print";
import { APIContext } from "../../../contexts";
import { QuickSearch } from "../../../components/molecules";

let location = "";

const MockLocation: FC = () => {
    location = useLocation().pathname;
    return null;
};

describe("QuickSearchTest", () => {
    let api: ColonyPrintAPI;

    const renderSearch = () =>
        render(
            <APIContext.Provider value={api}>
                <MemoryRouter initialEntries={["/"]}>
                    <QuickSearch />
                    <Routes>
                        <Route path="*" element={<MockLocation />} />
                    </Routes>
                </MemoryRouter>
            </APIContext.Provider>
        );

    const search = async (query: string) => {
        const input = screen.getByRole("searchbox", {
            name: "Go to node or job"
        });
        fireEvent.change(input, { target: { value: query } });
        await act(async () => {
            fireEvent.submit(input);
        });
        return input as HTMLInputElement;
    };

    beforeEach(() => {
        location = "";
        api = {
            listNodes: vi.fn().mockResolvedValue({
                "shop-1": { name: "Shop 1" },
                warehouse: { name: "Warehouse" }
            }),
            listJobs: vi.fn().mockResolvedValue({
                "4f1c9a2e7d": { id: "4f1c9a2e7d" },
                b7e30d51aa: { id: "b7e30d51aa" }
            })
        } as unknown as ColonyPrintAPI;
    });

    afterEach(() => {
        cleanup();
    });

    test("test_render", () => {
        renderSearch();
        expect(screen.getByRole("search")).toBeTruthy();
        expect(
            screen
                .getByRole("searchbox", { name: "Go to node or job" })
                .getAttribute("placeholder")
        ).toBe("Go to node or job");
        expect(screen.queryByRole("alert")).toBe(null);
        const key = document.querySelector(".quick-search-key");
        expect(key?.textContent).toBe("/");
        expect(key?.getAttribute("aria-hidden")).toBe("true");
    });

    test("test_focus", () => {
        renderSearch();
        const input = screen.getByRole("searchbox");
        const event = new KeyboardEvent("keydown", {
            key: "/",
            bubbles: true,
            cancelable: true
        });
        document.body.dispatchEvent(event);
        expect(document.activeElement).toBe(input);
        expect(event.defaultPrevented).toBe(true);
    });

    test("test_focus_ignored", () => {
        // the key is kept for the fields being typed into, and for
        // the shortcuts of the browser (e.g., the ones of its search)
        renderSearch();
        const input = screen.getByRole("searchbox");
        const field = document.createElement("textarea");
        document.body.appendChild(field);
        try {
            field.focus();
            const typed = new KeyboardEvent("keydown", {
                key: "/",
                bubbles: true,
                cancelable: true
            });
            field.dispatchEvent(typed);
            expect(document.activeElement).toBe(field);
            expect(typed.defaultPrevented).toBe(false);

            field.blur();
            for (const options of [
                { key: "/", ctrlKey: true },
                { key: "/", metaKey: true },
                { key: "a" }
            ]) {
                const event = new KeyboardEvent("keydown", {
                    ...options,
                    bubbles: true,
                    cancelable: true
                });
                document.body.dispatchEvent(event);
                expect(event.defaultPrevented).toBe(false);
            }
            expect(document.activeElement).not.toBe(input);
        } finally {
            field.remove();
        }
    });

    test("test_focus_unmount", () => {
        // the shortcut is gone with the search, so that it doesn't
        // take the key away from the pages without it
        renderSearch();
        cleanup();
        const event = new KeyboardEvent("keydown", {
            key: "/",
            bubbles: true,
            cancelable: true
        });
        document.body.dispatchEvent(event);
        expect(event.defaultPrevented).toBe(false);
    });

    test("test_search_node", async () => {
        renderSearch();
        const input = await search("Shop-1");
        expect(location).toBe("/nodes/shop-1");
        expect(input.value).toBe("");
        expect(input.readOnly).toBe(false);
    });

    test("test_search_job", async () => {
        renderSearch();
        await search("b7e3");
        expect(location).toBe("/jobs/b7e30d51aa");
    });

    test("test_search_missing", async () => {
        renderSearch();
        const input = await search(" nothing ");
        expect(location).toBe("/");
        expect(screen.getByRole("alert").textContent).toBe(
            'No node or job "nothing"'
        );
        expect(input.value).toBe(" nothing ");

        // the error is cleared as soon as the query is changed
        fireEvent.change(input, { target: { value: "shop" } });
        expect(screen.queryByRole("alert")).toBe(null);
    });

    test("test_search_empty", async () => {
        renderSearch();
        await search("   ");
        expect(api.listNodes).not.toHaveBeenCalled();
        expect(api.listJobs).not.toHaveBeenCalled();
        expect(location).toBe("/");
    });

    test("test_search_errors", async () => {
        // the jobs are still searched when the nodes can't be listed
        // (and the other way around), instead of failing the search
        api.listNodes = vi.fn().mockRejectedValue(new Error("Offline"));
        renderSearch();
        await search("4f1c");
        expect(location).toBe("/jobs/4f1c9a2e7d");

        api.listJobs = vi.fn().mockRejectedValue(new Error("Offline"));
        await search("4f1c");
        expect(screen.getByRole("alert").textContent).toBe(
            'No node or job "4f1c"'
        );
    });

    test("test_search_pending", async () => {
        // the query can't be changed while it's being searched
        let resolve: (value: unknown) => void = () => {};
        api.listNodes = vi
            .fn()
            .mockReturnValue(new Promise((r) => (resolve = r)));
        renderSearch();
        const input = screen.getByRole("searchbox") as HTMLInputElement;
        fireEvent.change(input, { target: { value: "warehouse" } });
        fireEvent.submit(input);
        expect(input.readOnly).toBe(true);
        await act(async () => {
            resolve({ warehouse: { name: "Warehouse" } });
        });
        expect(input.readOnly).toBe(false);
        expect(location).toBe("/nodes/warehouse");
    });
});
