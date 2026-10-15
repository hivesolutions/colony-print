import { describe, expect, test } from "vitest";

import { NodeInfo } from "../../api/colony-print";
import {
    ONLINE_THRESHOLD,
    compareVersions,
    isNodeBehind,
    isNodeOnline
} from "../../utils";

const mockNode = (values: Partial<NodeInfo>): NodeInfo =>
    ({ name: "node", ...values }) as NodeInfo;

describe("NodeTest", () => {
    test("test_is_node_online", () => {
        const node = mockNode({ last_ping: 1000 });
        expect(isNodeOnline(node, 1000)).toBe(true);
        expect(isNodeOnline(node, 1600)).toBe(true);
        expect(isNodeOnline(node, 1000 + ONLINE_THRESHOLD - 1)).toBe(true);
    });

    test("test_is_node_online_threshold", () => {
        const node = mockNode({ last_ping: 1000 });
        expect(isNodeOnline(node, 1000 + ONLINE_THRESHOLD)).toBe(false);
        expect(isNodeOnline(node, 1000 + ONLINE_THRESHOLD * 10)).toBe(false);
    });

    test("test_is_node_online_future", () => {
        // a node seen "after now" (the clock of the server ahead
        // of the one of the browser) is online, not offline
        const node = mockNode({ last_ping: 2000 });
        expect(isNodeOnline(node, 1000)).toBe(true);
    });

    test("test_is_node_online_missing", () => {
        expect(isNodeOnline(mockNode({}), 1000)).toBe(false);
        expect(isNodeOnline(null, 1000)).toBe(false);
        expect(isNodeOnline(undefined, 1000)).toBe(false);
    });

    test("test_is_node_online_now", () => {
        const now = Date.now() / 1000;
        expect(isNodeOnline(mockNode({ last_ping: now - 10 }))).toBe(true);
        expect(
            isNodeOnline(mockNode({ last_ping: now - ONLINE_THRESHOLD - 10 }))
        ).toBe(false);
    });

    test("test_compare_versions", () => {
        expect(compareVersions("0.24.0", "0.25.0") < 0).toBe(true);
        expect(compareVersions("0.25.0", "0.24.0") > 0).toBe(true);
        expect(compareVersions("0.25.0", "0.25.0")).toBe(0);
        expect(compareVersions("1.0.0", "0.99.99") > 0).toBe(true);
    });

    test("test_compare_versions_numeric", () => {
        // the parts are compared as numbers, not as strings, so
        // that "0.10.0" is newer than "0.9.0"
        expect(compareVersions("0.10.0", "0.9.0") > 0).toBe(true);
        expect(compareVersions("0.9.0", "0.10.0") < 0).toBe(true);
    });

    test("test_compare_versions_missing_parts", () => {
        expect(compareVersions("0.25", "0.25.0")).toBe(0);
        expect(compareVersions("0.25.1", "0.25") > 0).toBe(true);
        expect(compareVersions("0.25", "0.25.1") < 0).toBe(true);
        expect(compareVersions("", "0.0.0")).toBe(0);
    });

    test("test_compare_versions_invalid", () => {
        expect(compareVersions("abc", "0.0.0")).toBe(0);
        expect(compareVersions("1.0.0rc1", "1.0.0")).toBe(0);
        expect(compareVersions("x.1", "0.2") < 0).toBe(true);
    });

    test("test_is_node_behind", () => {
        expect(isNodeBehind(mockNode({ version: "0.24.0" }), "0.25.0")).toBe(
            true
        );
        expect(isNodeBehind(mockNode({ version: "0.25.0" }), "0.25.0")).toBe(
            false
        );
        expect(isNodeBehind(mockNode({ version: "0.26.0" }), "0.25.0")).toBe(
            false
        );
    });

    test("test_is_node_behind_missing", () => {
        expect(isNodeBehind(mockNode({}), "0.25.0")).toBe(false);
        expect(isNodeBehind(mockNode({ version: "0.24.0" }), null)).toBe(false);
        expect(isNodeBehind(mockNode({ version: "0.24.0" }), undefined)).toBe(
            false
        );
        expect(isNodeBehind(mockNode({ version: "0.24.0" }), "")).toBe(false);
        expect(isNodeBehind(null, "0.25.0")).toBe(false);
    });
});
