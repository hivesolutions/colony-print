import React from "react";
import { afterEach, describe, expect, test } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";
import { syncOutline } from "ionicons/icons";

import { Panel, PanelHeader } from "../../../components/molecules";

describe("PanelTest", () => {
    afterEach(() => {
        cleanup();
    });

    test("test_panel_header", () => {
        const { container } = render(<PanelHeader title="Properties" />);
        const heading = screen.getByRole("heading", { name: "Properties" });
        expect(heading.tagName).toBe("H3");
        expect(heading.className).toBe("title title-3 panel-title");
        expect(container.firstElementChild?.className).toBe("panel-header");
        expect(container.querySelector("ion-icon")).toBe(null);
        expect(container.querySelector(".panel-actions")).toBe(null);
    });

    test("test_panel_header_icon", () => {
        render(
            <PanelHeader
                title="Updates"
                icon={syncOutline}
                actions={<span>9</span>}
            />
        );
        const heading = screen.getByRole("heading", { name: "Updates" });
        expect(heading.querySelector("ion-icon")?.getAttribute("icon")).toBe(
            syncOutline
        );
        expect(screen.getByText("9").parentElement?.className).toBe(
            "panel-actions"
        );
    });

    test("test_panel", () => {
        const { container } = render(
            <Panel title="Libraries" icon={syncOutline} actions="5">
                <p>npcolony</p>
            </Panel>
        );
        const panel = container.firstElementChild as HTMLElement;
        expect(panel.className).toBe("card panel");
        expect(panel.children[0].className).toBe("panel-header");
        expect(panel.children[1].textContent).toBe("npcolony");
        expect(screen.getByRole("heading", { name: "Libraries" })).toBeTruthy();
        expect(container.querySelector(".panel-actions")?.textContent).toBe(
            "5"
        );
    });

    test("test_panel_style", () => {
        const { container } = render(
            <Panel title="Session" style={["settings-session"]} />
        );
        expect(container.firstElementChild?.className).toBe(
            "card panel settings-session"
        );
        expect(container.firstElementChild?.children.length).toBe(1);
    });
});
