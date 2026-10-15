import React from "react";
import { afterEach, describe, expect, test } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { DataTable } from "../../../components/molecules";

interface MockItem {
    name: string;
    count: number;
}

const COLUMNS = [
    {
        key: "name",
        header: "Name",
        render: (item: MockItem) => item.name
    },
    {
        key: "count",
        header: "Count",
        render: (item: MockItem) => <b>{item.count}</b>
    }
];

describe("DataTableTest", () => {
    afterEach(() => {
        cleanup();
    });

    test("test_render", () => {
        const { container } = render(
            <DataTable
                columns={COLUMNS}
                data={[
                    { name: "shop-1", count: 3 },
                    { name: "shop-2", count: 2 }
                ]}
            />
        );
        expect(container.firstElementChild?.className).toBe(
            "card data-table-card"
        );
        expect(
            Array.from(container.querySelectorAll("th")).map(
                (th) => th.textContent
            )
        ).toEqual(["Name", "Count"]);
        const rows = Array.from(container.querySelectorAll("tbody tr"));
        expect(
            rows.map((row) =>
                Array.from(row.querySelectorAll("td")).map((td) => [
                    td.textContent,
                    td.getAttribute("data-label")
                ])
            )
        ).toEqual([
            [
                ["shop-1", "Name"],
                ["3", "Count"]
            ],
            [
                ["shop-2", "Name"],
                ["2", "Count"]
            ]
        ]);
        expect(container.querySelector("table")?.parentElement?.className).toBe(
            "data-table-scroll"
        );
        expect(container.querySelector(".data-table-footer")).toBe(null);
    });

    test("test_render_empty", () => {
        const { container } = render(
            <DataTable columns={COLUMNS} data={[]} emptyMessage="No nodes" />
        );
        const cell = screen.getByText("No nodes");
        expect(cell.className).toBe("data-table-empty");
        expect(cell.getAttribute("colspan")).toBe("2");
        expect(container.querySelectorAll("tbody tr").length).toBe(1);
        cleanup();

        render(<DataTable columns={COLUMNS} data={[]} />);
        expect(screen.getByText("No data available")).toBeTruthy();
    });

    test("test_render_header", () => {
        // the header and the footer are kept in the card of the table,
        // the header above its columns and the footer below its rows
        const { container } = render(
            <DataTable
                columns={COLUMNS}
                data={[{ name: "shop-1", count: 3 }]}
                header={<div className="mock-header">Tabs</div>}
                footer="1 of 1 nodes"
            />
        );
        const card = container.firstElementChild as HTMLElement;
        expect(
            Array.from(card.children).map((child) => child.className)
        ).toEqual(["mock-header", "data-table-scroll", "data-table-footer"]);
        expect(card.lastElementChild?.textContent).toBe("1 of 1 nodes");
    });

    test("test_render_loading", () => {
        // while loading the header is kept (e.g., the filters), while
        // the rows and the footer (with their counts) are not shown
        const { container } = render(
            <DataTable
                columns={COLUMNS}
                data={[{ name: "shop-1", count: 3 }]}
                loading
                header={<div className="mock-header">Tabs</div>}
                footer="1 of 1 nodes"
            />
        );
        const card = container.firstElementChild as HTMLElement;
        expect(
            Array.from(card.children).map((child) => child.className)
        ).toEqual(["mock-header", "data-table-loading"]);
        expect(container.querySelector(".loader")).toBeTruthy();
        expect(container.querySelector("table")).toBe(null);
    });
});
