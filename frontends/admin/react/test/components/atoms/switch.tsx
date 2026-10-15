import React from "react";
import { afterEach, describe, expect, test, vi } from "vitest";
import { cleanup, fireEvent, render, screen } from "@testing-library/react";

import { Switch } from "../../../components/atoms";

describe("SwitchTest", () => {
    afterEach(() => {
        cleanup();
    });

    test("test_render", () => {
        render(<Switch aria-label="Auto-update" />);
        const control = screen.getByRole("switch", { name: "Auto-update" });
        expect(control.className).toBe("switch");
        expect(control.getAttribute("aria-checked")).toBe("false");
        expect(control.getAttribute("type")).toBe("button");
        expect(control.firstElementChild?.className).toBe("switch-thumb");
    });

    test("test_render_checked", () => {
        render(<Switch aria-label="Auto-update" checked style={["mock"]} />);
        const control = screen.getByRole("switch", { name: "Auto-update" });
        expect(control.className).toBe("switch switch-checked mock");
        expect(control.getAttribute("aria-checked")).toBe("true");
    });

    test("test_change", () => {
        const onChange = vi.fn();
        const { rerender } = render(
            <Switch aria-label="Auto-update" onChange={onChange} />
        );
        fireEvent.click(screen.getByRole("switch"));
        expect(onChange).toHaveBeenLastCalledWith(true);

        // the switch is controlled, so that it's the (checked) value
        // provided that is toggled, not the one of the last click
        rerender(
            <Switch aria-label="Auto-update" checked onChange={onChange} />
        );
        fireEvent.click(screen.getByRole("switch"));
        expect(onChange).toHaveBeenLastCalledWith(false);
        expect(onChange).toHaveBeenCalledTimes(2);
    });

    test("test_change_missing", () => {
        // a switch without a handler is a read only one
        render(<Switch aria-label="Auto-update" checked />);
        fireEvent.click(screen.getByRole("switch"));
        expect(screen.getByRole("switch").getAttribute("aria-checked")).toBe(
            "true"
        );
    });

    test("test_change_disabled", () => {
        const onChange = vi.fn();
        render(
            <Switch aria-label="Auto-update" disabled onChange={onChange} />
        );
        fireEvent.click(screen.getByRole("switch"));
        expect(onChange).not.toHaveBeenCalled();
    });
});
