import { NodeInfo } from "../api/colony-print";

/**
 * The time (in seconds) since the last time a node was seen
 * after which it's considered offline, longer than the time a
 * node waits for its jobs (up to 10 minutes) before it registers
 * itself again, the node being seen as well when it picks its
 * jobs up, so that it's not offline while printing them.
 */
export const ONLINE_THRESHOLD = 900;

/**
 * Checks if the node was seen (registered itself) recently
 * enough to be considered online, a node never seen being
 * offline.
 */
export const isNodeOnline = (
    node?: NodeInfo | null,
    now: number = Date.now() / 1000
): boolean => {
    if (!node?.last_ping) return false;
    return now - node.last_ping < ONLINE_THRESHOLD;
};

/**
 * Compares two (dotted) versions (e.g., "0.24.0" and "0.25.0")
 * part by part as numbers, returning a negative number when the
 * first one is older, a positive one when it's newer and zero
 * when they're the same, a missing part counting as zero.
 */
export const compareVersions = (first: string, second: string): number => {
    const firstParts = first.split(".");
    const secondParts = second.split(".");
    const length = Math.max(firstParts.length, secondParts.length);
    for (let index = 0; index < length; index++) {
        const difference =
            (parseInt(firstParts[index], 10) || 0) -
            (parseInt(secondParts[index], 10) || 0);
        if (difference !== 0) return difference;
    }
    return 0;
};

/**
 * Checks if the node runs an older version than the one of the
 * server (e.g., a node that doesn't update itself), which is
 * unknown (and so not behind) when either version is missing.
 */
export const isNodeBehind = (
    node?: NodeInfo | null,
    version?: string | null
): boolean => {
    if (!node?.version || !version) return false;
    return compareVersions(node.version, version) < 0;
};
