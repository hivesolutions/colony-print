import React from "react";
import { afterEach, describe, expect, test } from "vitest";
import { cleanup, render } from "@testing-library/react";
import { printOutline } from "ionicons/icons";

import { Icon } from "../../../components/atoms";

describe("IconTest", () => {
    afterEach(() => {
        cleanup();
    });

    test("test_render", () => {
        const { container } = render(<Icon icon={printOutline} />);
        const icon = container.querySelector("ion-icon");
        expect(icon === null).toBe(false);
        expect(icon?.getAttribute("icon")).toBe(printOutline);
        expect(icon?.getAttribute("class")).toBe("icon icon-md");
        expect(icon?.getAttribute("aria-hidden")).toBe("true");
        expect(icon?.getAttribute("role")).toBe(null);
        expect(icon?.getAttribute("aria-label")).toBe(null);
    });

    test("test_render_size", () => {
        const { container } = render(<Icon icon={printOutline} size="lg" />);
        const icon = container.querySelector("ion-icon");
        expect(icon?.getAttribute("class")).toBe("icon icon-lg");
    });

    test("test_render_label", () => {
        const { container } = render(
            <Icon icon={printOutline} label="Printers" />
        );
        const icon = container.querySelector("ion-icon");
        expect(icon?.getAttribute("role")).toBe("img");
        expect(icon?.getAttribute("aria-label")).toBe("Printers");
        expect(icon?.getAttribute("aria-hidden")).toBe(null);
    });

    test("test_render_style", () => {
        const { container } = render(
            <Icon icon={printOutline} style={["side-bar-icon", ""]} />
        );
        const icon = container.querySelector("ion-icon");
        expect(icon?.getAttribute("class")).toBe("icon icon-md side-bar-icon");
    });
});
