import { JobInfo } from "../api/colony-print";

interface NodeVersions {
    version?: string;
    libraries?: Record<string, string>;
}

/**
 * The types of the jobs that are commands for the nodes (e.g.,
 * their restart), instead of documents to be printed.
 */
export const COMMAND_TYPES = ["restart", "update", "auto-update"];

/**
 * The types of the (command) jobs that restart their node.
 */
export const RESTART_TYPES = ["restart", "update"];

/**
 * Checks if the job is a command for its node, which has
 * no payload and can not be duplicated.
 */
export const isCommandJob = (job?: JobInfo | null): boolean => {
    return !!job?.type && COMMAND_TYPES.includes(job.type);
};

/**
 * Checks if the job is going to restart its node, meaning
 * that it's a restart (or an update) queued or in flight.
 */
export const isRestartPending = (job?: JobInfo | null): boolean => {
    if (!job?.type || !RESTART_TYPES.includes(job.type)) return false;
    return job.status === "queued" || job.status === "printing";
};

/**
 * Formats the version of the node before and after its restart,
 * as kept in the result of the jobs that restart it (e.g.,
 * "0.23.0 → 0.24.0").
 */
export const formatVersions = (job?: JobInfo | null): string => {
    const before = job?.result?.before as NodeVersions | undefined;
    const after = job?.result?.after as NodeVersions | undefined;
    if (!before || !after) return "-";
    if (before.version === after.version) return after.version || "-";
    return `${before.version || "-"} → ${after.version || "-"}`;
};

/**
 * Formats the libraries of the node whose version changed with
 * its restart, as kept in the result of the jobs that restart
 * it (e.g., "npcolony 1.6.0 → 1.7.0").
 */
export const formatLibraries = (job?: JobInfo | null): string => {
    const before = job?.result?.before as NodeVersions | undefined;
    const after = job?.result?.after as NodeVersions | undefined;
    if (!before || !after) return "-";
    const previous = before.libraries || {};
    const current = after.libraries || {};
    const names = Object.keys({ ...previous, ...current }).sort();
    return (
        names
            .filter((name) => previous[name] !== current[name])
            .map(
                (name) =>
                    `${name} ${previous[name] || "-"} → ${current[name] || "-"}`
            )
            .join(", ") || "-"
    );
};
