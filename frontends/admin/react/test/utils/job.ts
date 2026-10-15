import { describe, expect, test } from "vitest";

import { JobInfo } from "../../api/colony-print";
import {
    STATUS_VARIANTS,
    countJobs,
    formatLibraries,
    formatStatus,
    formatVersions,
    isCommandJob,
    isRestartPending
} from "../../utils";

const mockJob = (values: Partial<JobInfo>): JobInfo =>
    ({ id: "job", node_id: "node", status: "queued", ...values }) as JobInfo;

describe("JobTest", () => {
    test("test_status_variants", () => {
        expect(
            ["finished", "printing", "queued", "cancelled"].map((status) =>
                STATUS_VARIANTS.get(status)
            )
        ).toEqual(["success", "warning", "info", "default"]);

        // an unknown status has no variant, being shown as default
        expect(STATUS_VARIANTS.get("unknown")).toBe(undefined);
    });

    test("test_is_command_job", () => {
        expect(isCommandJob(mockJob({ type: "restart" }))).toBe(true);
        expect(isCommandJob(mockJob({ type: "update" }))).toBe(true);
        expect(isCommandJob(mockJob({ type: "auto-update" }))).toBe(true);
        expect(isCommandJob(mockJob({ type: "npcolony" }))).toBe(false);
        expect(isCommandJob(mockJob({}))).toBe(false);
        expect(isCommandJob(null)).toBe(false);
    });

    test("test_is_restart_pending", () => {
        expect(
            isRestartPending(mockJob({ type: "restart", status: "queued" }))
        ).toBe(true);
        expect(
            isRestartPending(mockJob({ type: "update", status: "printing" }))
        ).toBe(true);
        expect(
            isRestartPending(mockJob({ type: "restart", status: "finished" }))
        ).toBe(false);
        expect(
            isRestartPending(mockJob({ type: "auto-update", status: "queued" }))
        ).toBe(false);
        expect(isRestartPending(undefined)).toBe(false);
    });

    test("test_format_status", () => {
        expect(formatStatus("printing")).toBe("Printing");
        expect(formatStatus("finished")).toBe("Finished");
        expect(formatStatus("x")).toBe("X");
        expect(formatStatus("")).toBe("-");
        expect(formatStatus(undefined)).toBe("-");
        expect(formatStatus(null)).toBe("-");
    });

    test("test_format_versions", () => {
        expect(
            formatVersions(
                mockJob({
                    result: {
                        before: { version: "0.24.0" },
                        after: { version: "0.25.0" }
                    }
                })
            )
        ).toBe("0.24.0 → 0.25.0");
        expect(
            formatVersions(
                mockJob({
                    result: {
                        before: { version: "0.25.0" },
                        after: { version: "0.25.0" }
                    }
                })
            )
        ).toBe("0.25.0");
        expect(
            formatVersions(
                mockJob({
                    result: { before: {}, after: { version: "0.25.0" } }
                })
            )
        ).toBe("- → 0.25.0");
        expect(
            formatVersions(
                mockJob({
                    result: { before: { version: "0.24.0" }, after: {} }
                })
            )
        ).toBe("0.24.0 → -");
        expect(
            formatVersions(mockJob({ result: { before: {}, after: {} } }))
        ).toBe("-");
        expect(formatVersions(mockJob({ result: {} }))).toBe("-");
        expect(formatVersions(null)).toBe("-");
    });

    test("test_format_libraries", () => {
        expect(
            formatLibraries(
                mockJob({
                    result: {
                        before: {
                            libraries: { npcolony: "1.6.0", pillow: "11" }
                        },
                        after: {
                            libraries: { npcolony: "1.7.0", pillow: "11" }
                        }
                    }
                })
            )
        ).toBe("npcolony 1.6.0 → 1.7.0");
        expect(
            formatLibraries(
                mockJob({
                    result: {
                        before: { libraries: { pillow: "11" } },
                        after: { libraries: { npcolony: "1.7.0" } }
                    }
                })
            )
        ).toBe("npcolony - → 1.7.0, pillow 11 → -");
        expect(
            formatLibraries(mockJob({ result: { before: {}, after: {} } }))
        ).toBe("-");
        expect(formatLibraries(undefined)).toBe("-");
    });

    test("test_count_jobs", () => {
        const counts = countJobs([
            mockJob({ status: "finished", result: { result: "success" } }),
            mockJob({ status: "finished", result: { result: "success" } }),
            mockJob({ status: "finished", result: { result: "error" } }),
            mockJob({ status: "printing" }),
            mockJob({ status: "queued" }),
            mockJob({ status: "queued" }),
            mockJob({ status: "cancelled" })
        ]);
        expect(counts).toEqual({
            succeeded: 2,
            failed: 1,
            printing: 1,
            queued: 2,
            cancelled: 1
        });
    });

    test("test_count_jobs_without_result", () => {
        // a finished job without a result is failed, as the server
        // counts it for the statistics of the nodes
        const counts = countJobs([mockJob({ status: "finished" })]);
        expect(counts.failed).toBe(1);
        expect(counts.succeeded).toBe(0);
    });

    test("test_count_jobs_unknown", () => {
        const counts = countJobs([mockJob({ status: "unknown" })]);
        expect(counts).toEqual({
            succeeded: 0,
            failed: 0,
            printing: 0,
            queued: 0,
            cancelled: 0
        });
    });

    test("test_count_jobs_empty", () => {
        expect(countJobs([])).toEqual({
            succeeded: 0,
            failed: 0,
            printing: 0,
            queued: 0,
            cancelled: 0
        });
    });
});
