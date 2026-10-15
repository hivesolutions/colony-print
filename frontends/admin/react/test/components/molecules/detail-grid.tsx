import React from "react";
import { afterEach, describe, expect, test } from "vitest";
import { cleanup, render } from "@testing-library/react";

import { DetailGrid } from "../../../components/molecules";

describe("DetailGridTest", () => {
    afterEach(() => {
        cleanup();
    });

    test("test_render", () => {
        const { container } = render(
            <DetailGrid
                fields={[
                    { label: "Location", value: "Porto" },
                    { label: "Version", value: <code>0.25.0</code> }
                ]}
            />
        );
        expect(container.firstElementChild?.className).toBe(
            "card detail-grid-card"
        );
        const rows = Array.from(container.querySelectorAll(".detail-grid-row"));
        expect(
            rows.map((row) => [
                row.querySelector("dt")?.textContent,
                row.querySelector("dd")?.textContent
            ])
        ).toEqual([
            ["Location", "Porto"],
            ["Version", "0.25.0"]
        ]);
        expect(container.querySelector("dd code")).toBeTruthy();
    });

    test("test_render_header", () => {
        const { container } = render(
            <DetailGrid
                header={<div className="mock-header">Properties</div>}
                fields={[{ label: "Location", value: "Porto" }]}
            />
        );
        const card = container.firstElementChild as HTMLElement;
        expect(
            Array.from(card.children).map((child) => child.className)
        ).toEqual(["mock-header", "detail-grid"]);
    });

    test("test_render_loading", () => {
        const { container } = render(
            <DetailGrid
                header={<div className="mock-header">Properties</div>}
                fields={[{ label: "Location", value: "Porto" }]}
                loading
            />
        );
        const card = container.firstElementChild as HTMLElement;
        expect(
            Array.from(card.children).map((child) => child.className)
        ).toEqual(["mock-header", "detail-grid-loading"]);
        expect(container.querySelector(".loader")).toBeTruthy();
        expect(container.querySelector("dl")).toBe(null);
    });

    test("test_render_empty", () => {
        const { container } = render(<DetailGrid fields={[]} />);
        expect(container.querySelector("dl")?.children.length).toBe(0);
    });
});
