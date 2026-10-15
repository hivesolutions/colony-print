import { describe, expect, test } from "vitest";

import { findSearchTarget, getBreadcrumbs } from "../../utils";

describe("NavigationTest", () => {
    test("test_get_breadcrumbs", () => {
        expect(getBreadcrumbs("/")).toEqual([
            { label: "Dashboard", path: "/" }
        ]);
        expect(getBreadcrumbs("/nodes")).toEqual([
            { label: "Nodes", path: "/nodes" }
        ]);
        expect(getBreadcrumbs("/nodes/shop-1")).toEqual([
            { label: "Nodes", path: "/nodes" },
            { label: "shop-1", path: "/nodes/shop-1" }
        ]);
        expect(getBreadcrumbs("/jobs/4f1c9a2e/")).toEqual([
            { label: "Jobs", path: "/jobs" },
            { label: "4f1c9a2e", path: "/jobs/4f1c9a2e" }
        ]);
        expect(getBreadcrumbs("/settings")).toEqual([
            { label: "Settings", path: "/settings" }
        ]);
    });

    test("test_get_breadcrumbs_unknown", () => {
        expect(getBreadcrumbs("/unknown")).toEqual([
            { label: "Dashboard", path: "/" }
        ]);
        expect(getBreadcrumbs("")).toEqual([{ label: "Dashboard", path: "/" }]);

        // the names of the properties of the objects are not sections
        // (e.g., "constructor"), as they'd be taken as their labels
        expect(getBreadcrumbs("/constructor")).toEqual([
            { label: "Dashboard", path: "/" }
        ]);
        expect(getBreadcrumbs("/toString/value")).toEqual([
            { label: "Dashboard", path: "/" }
        ]);
    });

    test("test_get_breadcrumbs_encoded", () => {
        expect(getBreadcrumbs("/nodes/shop%201")).toEqual([
            { label: "Nodes", path: "/nodes" },
            { label: "shop 1", path: "/nodes/shop%201" }
        ]);
        expect(getBreadcrumbs("/nodes/100%")).toEqual([
            { label: "Nodes", path: "/nodes" },
            { label: "100%", path: "/nodes/100%" }
        ]);
    });

    test("test_find_search_target", () => {
        const nodeIds = ["shop-1", "Warehouse"];
        const jobIds = ["4f1c9a2e7d", "4f1c0000aa", "b7e30d51aa"];
        expect(findSearchTarget("shop-1", nodeIds, jobIds)).toBe(
            "/nodes/shop-1"
        );
        expect(findSearchTarget("  warehouse ", nodeIds, jobIds)).toBe(
            "/nodes/Warehouse"
        );
        expect(findSearchTarget("b7e30d51aa", nodeIds, jobIds)).toBe(
            "/jobs/b7e30d51aa"
        );
        expect(findSearchTarget("B7E3", nodeIds, jobIds)).toBe(
            "/jobs/b7e30d51aa"
        );
    });

    test("test_find_search_target_ambiguous", () => {
        const jobIds = ["4f1c9a2e7d", "4f1c0000aa"];
        expect(findSearchTarget("4f1c", [], jobIds)).toBe(null);
        expect(findSearchTarget("4f1c9", [], jobIds)).toBe("/jobs/4f1c9a2e7d");
    });

    test("test_find_search_target_exact", () => {
        // an identifier that is also the start of another one is
        // found by itself, instead of being taken as ambiguous
        const jobIds = ["4f1c", "4f1c9a2e7d"];
        expect(findSearchTarget("4f1c", [], jobIds)).toBe("/jobs/4f1c");
    });

    test("test_find_search_target_node_first", () => {
        expect(findSearchTarget("shared", ["shared"], ["shared"])).toBe(
            "/nodes/shared"
        );
    });

    test("test_find_search_target_missing", () => {
        expect(findSearchTarget("nothing", ["shop-1"], ["4f1c"])).toBe(null);
        expect(findSearchTarget("", ["shop-1"], ["4f1c"])).toBe(null);
        expect(findSearchTarget("   ", ["shop-1"], ["4f1c"])).toBe(null);
        expect(findSearchTarget("shop", ["shop-1"], [])).toBe(null);
    });

    test("test_find_search_target_encoded", () => {
        expect(findSearchTarget("shop 1", ["shop 1"], [])).toBe(
            "/nodes/shop%201"
        );
        expect(findSearchTarget("a/b", [], ["a/b"])).toBe("/jobs/a%2Fb");
    });
});
