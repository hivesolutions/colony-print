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
