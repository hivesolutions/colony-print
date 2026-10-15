import React from "react";
import { afterEach, describe, expect, test } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { ContentHeader } from "../../../components/molecules";

describe("ContentHeaderTest", () => {
    afterEach(() => {
        cleanup();
    });

    test("test_render", () => {
        const { container } = render(
            <ContentHeader
                title="Nodes"
                description="Registered print nodes"
                actions={<button>Refresh</button>}
            />
        );
        const heading = screen.getByRole("heading", { name: "Nodes" });
        expect(heading.tagName).toBe("H1");
        expect(heading.parentElement?.className).toBe("content-header-title");
        expect(screen.getByText("Registered print nodes").className).toBe(
            "text text-secondary"
        );
        expect(
            screen.getByRole("button", { name: "Refresh" }).parentElement
                ?.className
        ).toBe("content-header-actions");
        expect(container.firstElementChild?.className).toBe("content-header");
    });

    test("test_render_meta", () => {
        // the meta is shown next to the title (e.g., the identifier
        // and the state of the node), on the same row
        render(
            <ContentHeader
                title="Shop 1"
                meta={<span className="mock-meta">shop-1</span>}
            />
        );
        const meta = screen.getByText("shop-1");
        expect(meta.className).toBe("mock-meta");
        expect(meta.parentElement?.className).toBe("content-header-title");
        expect(meta.previousElementSibling?.textContent).toBe("Shop 1");
    });

    test("test_render_missing", () => {
        const { container } = render(<ContentHeader title="Jobs" />);
        expect(container.querySelector(".text")).toBe(null);
        expect(container.querySelector(".content-header-actions")).toBe(null);
        expect(
            container.querySelector(".content-header-title")?.children.length
        ).toBe(1);
    });
});
