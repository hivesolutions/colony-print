import React from "react";
import { afterEach, describe, expect, test } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { DistributionBar } from "../../../components/molecules";

describe("DistributionBarTest", () => {
    afterEach(() => {
        cleanup();
    });

    test("test_render", () => {
        const { container } = render(
            <DistributionBar
                title="Jobs by Status"
                description="The jobs kept by the server"
                items={[
                    { label: "Succeeded", count: 91, variant: "success" },
                    { label: "Failed", count: 1, variant: "error" },
                    { label: "Queued", count: 0, variant: "info" }
                ]}
            />
        );
        expect(
            screen.getByRole("heading", { name: "Jobs by Status" })
        ).toBeTruthy();
        expect(screen.getByText("The jobs kept by the server").className).toBe(
            "text text-small distribution-bar-description"
        );

        // the segments of the empty items are left out of the bar,
        // the other ones growing by their count
        const segments = Array.from(
            container.querySelectorAll<HTMLElement>(".distribution-bar-segment")
        );
        expect(segments.map((segment) => segment.className)).toEqual([
            "distribution-bar-segment distribution-bar-success",
            "distribution-bar-segment distribution-bar-error"
        ]);
        expect(segments.map((segment) => segment.style.flexGrow)).toEqual([
            "91",
            "1"
        ]);
        expect(
            container
                .querySelector(".distribution-bar-track")
                ?.getAttribute("aria-hidden")
        ).toBe("true");

        // while the legend lists every item, the empty ones included
        const items = Array.from(
            container.querySelectorAll(".distribution-bar-item")
        );
        expect(items.map((item) => item.textContent)).toEqual([
            "Succeeded91",
            "Failed1",
            "Queued0"
        ]);
    });

    test("test_render_empty", () => {
        const { container } = render(
            <DistributionBar
                title="Jobs by Status"
                items={[{ label: "Succeeded", count: 0, variant: "success" }]}
            />
        );
        expect(
            container.querySelectorAll(".distribution-bar-segment").length
        ).toBe(0);
        expect(
            container.querySelectorAll(".distribution-bar-item").length
        ).toBe(1);
    });

    test("test_render_description", () => {
        const { container } = render(
            <DistributionBar title="Jobs by Status" items={[]} />
        );
        expect(container.querySelector(".text-small")).toBe(null);
    });
});
