import React from "react";
import { afterEach, describe, expect, test } from "vitest";
import { cleanup, render, screen } from "@testing-library/react";

import { Logo } from "../../../components/atoms";

describe("LogoTest", () => {
    afterEach(() => {
        cleanup();
    });

    test("test_render", () => {
        render(<Logo />);
        const logo = screen.getByRole("img", { name: "Colony Print" });
        expect(logo.getAttribute("class")).toBe("logo");
        expect(logo.getAttribute("viewBox")).toBe("-3 -9 416 71.5");
        expect(logo.getAttribute("height")).toBe("32");
        expect(Number(logo.getAttribute("width"))).toBeCloseTo(
            (32 * 416) / 71.5
        );

        // the mark is drawn in its three slices, the middle one in
        // the brand mint, and the logotype in its three clipped ones
        expect(logo.querySelectorAll(".logo-ink").length).toBe(2);
        expect(logo.querySelectorAll(".logo-mint").length).toBe(1);
        expect(logo.querySelectorAll("clipPath").length).toBe(3);
        expect(logo.querySelectorAll(".logo-ink-stroke").length).toBe(2);
        expect(logo.querySelectorAll(".logo-mint-stroke").length).toBe(1);
    });

    test("test_render_aligned", () => {
        // the middle slice of the logotype is never shifted, so that
        // its letters stay aligned, only the one of the mark is
        const { container } = render(<Logo variant="logotype" />);
        const middle = container.querySelector(".logo-mint-stroke");
        expect(middle?.getAttribute("transform")).toBe(null);
    });

    test("test_render_clips", () => {
        const { container } = render(<Logo variant="logotype" />);
        const ids = Array.from(container.querySelectorAll("clipPath")).map(
            (clip) => clip.getAttribute("id")
        );
        const paths = Array.from(container.querySelectorAll("path")).map(
            (path) => path.getAttribute("clip-path")
        );
        expect(paths).toEqual(ids.map((id) => `url(#${id})`));
        expect(ids.every((id) => id && !id.includes(":"))).toBe(true);
    });

    test("test_render_unique", () => {
        // each logo has its own clip paths, so that two logos in the
        // same page (e.g., the side bar and the login) don't share them
        const { container } = render(
            <>
                <Logo />
                <Logo />
            </>
        );
        const ids = Array.from(container.querySelectorAll("clipPath")).map(
            (clip) => clip.getAttribute("id")
        );
        expect(ids.length).toBe(6);
        expect(new Set(ids).size).toBe(6);
    });

    test("test_render_solid", () => {
        const { container } = render(<Logo sliced={false} />);
        expect(container.querySelectorAll("clipPath").length).toBe(0);
        expect(container.querySelectorAll(".logo-ink-stroke").length).toBe(1);
        expect(container.querySelectorAll(".logo-mint-stroke").length).toBe(0);
        expect(container.querySelectorAll(".logo-mint").length).toBe(1);
    });

    test("test_render_mark", () => {
        render(<Logo variant="mark" height={24} />);
        const logo = screen.getByRole("img", { name: "Colony Print" });
        expect(logo.getAttribute("viewBox")).toBe("0 0 64 64");
        expect(logo.getAttribute("width")).toBe("24");
        expect(logo.getAttribute("height")).toBe("24");
        expect(logo.querySelectorAll("clipPath").length).toBe(0);
        expect(logo.querySelectorAll(".logo-ink-stroke").length).toBe(0);
    });

    test("test_render_logotype", () => {
        render(<Logo variant="logotype" height={71.5} />);
        const logo = screen.getByRole("img", { name: "Colony Print" });
        expect(logo.getAttribute("viewBox")).toBe("-3 -9 350 71.5");
        expect(logo.getAttribute("width")).toBe("350");
        expect(logo.querySelectorAll(".logo-mint").length).toBe(0);
    });

    test("test_render_label", () => {
        const { container } = render(<Logo label="" />);
        const logo = container.querySelector("svg");
        expect(logo?.getAttribute("role")).toBe(null);
        expect(logo?.getAttribute("aria-label")).toBe(null);
        expect(logo?.getAttribute("aria-hidden")).toBe("true");
    });

    test("test_render_style", () => {
        const { container } = render(<Logo style={["side-bar-logo", ""]} />);
        expect(container.querySelector("svg")?.getAttribute("class")).toBe(
            "logo side-bar-logo"
        );
    });
});
