/**
 * Formats a Unix timestamp (seconds) into a human-readable
 * date and time string using the browser's locale.
 */
export const formatTimestamp = (timestamp?: number): string => {
    if (timestamp === undefined || timestamp === null) return "-";
    const date = new Date(timestamp * 1000);
    return date.toLocaleString();
};

/**
 * Formats a duration in seconds into a human-readable
 * string (e.g., "2h 15m", "3d 4h").
 */
export const formatDuration = (seconds?: number | null): string => {
    if (seconds === undefined || seconds === null) return "-";
    if (seconds < 60) return `${Math.floor(seconds)}s`;
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`;
    if (seconds < 86400) {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        return m > 0 ? `${h}h ${m}m` : `${h}h`;
    }
    const d = Math.floor(seconds / 86400);
    const h = Math.floor((seconds % 86400) / 3600);
    return h > 0 ? `${d}d ${h}h` : `${d}d`;
};

/**
 * Formats a Unix timestamp (seconds) into a relative time
 * string (e.g., "2 minutes ago", "1 hour ago").
 */
export const formatRelativeTime = (timestamp?: number): string => {
    if (timestamp === undefined || timestamp === null) return "-";
    const now = Date.now() / 1000;
    const diff = now - timestamp;
    if (diff < 60) return "just now";
    if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
    return `${Math.floor(diff / 86400)}d ago`;
};
