import React from "react";
import { afterEach, describe, expect, test } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { serverOutline } from "ionicons/icons";

import { StatCard } from "../../../components/molecules";

describe("StatCardTest", () => {
    afterEach(() => {
        cleanup();
    });

    test("test_render", () => {
        const { container } = render(
            <StatCard label="Nodes" value={5} description="4 online" />
        );
        expect(screen.getByText("Nodes").className).toBe(
            "text text-secondary stat-card-label"
        );
        expect(screen.getByText("5").className).toBe(
            "title title-2 stat-card-value"
        );
        expect(screen.getByText("4 online").className).toBe(
            "text text-secondary stat-card-description"
        );
        expect(container.querySelector("ion-icon")).toBe(null);
    });

    test("test_render_icon", () => {
        const { container } = render(
            <StatCard label="Nodes" value={5} icon={serverOutline} />
        );
        const icon = container.querySelector(".stat-card-label ion-icon");
        expect(icon?.getAttribute("icon")).toBe(serverOutline);
        expect(icon?.getAttribute("class")).toBe("icon icon-sm");
    });

    test("test_render_description", () => {
        const { container } = render(<StatCard label="Jobs" value="-" />);
        expect(container.querySelector(".stat-card-description")).toBe(null);
    });

    test("test_render_nodes", () => {
        // both the value and the description may be elements, as
        // the health with its status or the counts with their colors
        const { container } = render(
            <StatCard
                label="API"
                value={<span className="mock-value">Healthy</span>}
                description={
                    <>
                        <span className="mock-online">4 online</span>, 1 offline
                    </>
                }
            />
        );
        expect(
            container.querySelector(".stat-card-value .mock-value")?.textContent
        ).toBe("Healthy");
        expect(
            container.querySelector(".stat-card-description")?.textContent
        ).toBe("4 online, 1 offline");
        expect(container.querySelector(".mock-online")).toBeTruthy();
    });

    test("test_render_style", () => {
        const { container } = render(
            <StatCard
                label="Errored"
                value={1}
                style={["node-show-stat-error"]}
            />
        );
        expect(container.firstElementChild?.className).toBe(
            "card stat-card node-show-stat-error"
        );
    });
});
