import React from "react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { FilterTabs } from "../../../components/molecules";

describe("FilterTabsTest", () => {
    afterEach(() => {
        cleanup();
    });

    test("test_render", () => {
        render(
            <FilterTabs
                label="Filter by state"
                value="online"
                onChange={() => {}}
                tabs={[
                    { value: "all", label: "All", count: 5 },
                    { value: "online", label: "Online", count: 4 },
                    { value: "offline", label: "Offline", count: 0 }
                ]}
            />
        );
        const group = screen.getByRole("group", { name: "Filter by state" });
        expect(group.className).toBe("filter-tabs filter-tabs-segmented");
        const tabs = Array.from(group.querySelectorAll("button"));
        expect(tabs.map((tab) => tab.textContent)).toEqual([
            "All5",
            "Online4",
            "Offline0"
        ]);
        expect(tabs.map((tab) => tab.getAttribute("aria-pressed"))).toEqual([
            "false",
            "true",
            "false"
        ]);
        expect(tabs.map((tab) => tab.className)).toEqual([
            "filter-tabs-tab",
            "filter-tabs-tab filter-tabs-tab-active",
            "filter-tabs-tab"
        ]);
        expect(tabs.every((tab) => tab.getAttribute("type") === "button")).toBe(
            true
        );
    });

    test("test_render_count", () => {
        const { container } = render(
            <FilterTabs
                value="all"
                onChange={() => {}}
                tabs={[{ value: "all", label: "All" }]}
            />
        );
        expect(container.querySelector(".filter-tabs-count")).toBe(null);
        expect(screen.getByRole("button").textContent).toBe("All");
    });

    test("test_render_variant", () => {
        render(
            <FilterTabs
                label="Filter by status"
                variant="underline"
                value="all"
                onChange={() => {}}
                tabs={[{ value: "all", label: "All", count: 8 }]}
            />
        );
        expect(
            screen.getByRole("group", { name: "Filter by status" }).className
        ).toBe("filter-tabs filter-tabs-underline");
    });

    test("test_change", () => {
        const onChange = vi.fn();
        render(
            <FilterTabs
                value="all"
                onChange={onChange}
                tabs={[
                    { value: "all", label: "All" },
                    { value: "queued", label: "Queued" }
                ]}
            />
        );
        fireEvent.click(screen.getByRole("button", { name: "Queued" }));
        expect(onChange).toHaveBeenCalledWith("queued");
        fireEvent.click(screen.getByRole("button", { name: "All" }));
        expect(onChange).toHaveBeenLastCalledWith("all");
        expect(onChange).toHaveBeenCalledTimes(2);
    });
});
