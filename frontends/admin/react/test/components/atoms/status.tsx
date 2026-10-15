import React from "react";
import { afterEach, describe, expect, test } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { Status } from "../../../components/atoms";

describe("StatusTest", () => {
    afterEach(() => {
        cleanup();
    });

    test("test_render", () => {
        const { container } = render(<Status>Cancelled</Status>);
        const status = container.firstElementChild as HTMLElement;
        expect(status.className).toBe("status status-default");
        expect(status.textContent).toBe("Cancelled");
        expect(status.firstElementChild?.className).toBe("status-dot");
    });

    test("test_render_variant", () => {
        const { container } = render(
            <>
                <Status variant="success">Finished</Status>
                <Status variant="error">Failed</Status>
                <Status variant="warning">Printing</Status>
                <Status variant="info">Queued</Status>
            </>
        );
        expect(
            Array.from(container.children).map((status) => status.className)
        ).toEqual([
            "status status-success",
            "status status-error",
            "status status-warning",
            "status status-info"
        ]);
    });

    test("test_render_style", () => {
        const { container } = render(
            <Status variant="success" style={["dashboard-health"]}>
                Healthy
            </Status>
        );
        expect(container.firstElementChild?.className).toBe(
            "status status-success dashboard-health"
        );
    });

    test("test_render_dot", () => {
        // without a label the status is only its dot, that is named
        // by its (provided) attributes instead
        render(<Status variant="success" role="img" aria-label="Online" />);
        const status = screen.getByRole("img", { name: "Online" });
        expect(status.textContent).toBe("");
        expect(status.querySelectorAll(".status-dot").length).toBe(1);
    });
});
