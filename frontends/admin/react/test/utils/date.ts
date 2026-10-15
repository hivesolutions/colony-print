import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import {
    formatDuration,
    formatRelativeTime,
    formatTime,
    formatTimestamp
} from "../../utils";

const NOW = new Date(2026, 9, 15, 14, 33, 12).getTime() / 1000;

describe("DateTest", () => {
    beforeEach(() => {
        vi.useFakeTimers();
        vi.setSystemTime(NOW * 1000);
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    test("test_format_timestamp", () => {
        expect(formatTimestamp(NOW)).toBe(
            new Date(NOW * 1000).toLocaleString()
        );
        expect(formatTimestamp(undefined)).toBe("-");
    });

    test("test_format_time", () => {
        // the timestamps of today are shown as their time of day,
        // from its start to its very end
        const morning = new Date(2026, 9, 15, 0, 0, 0).getTime() / 1000;
        const night = new Date(2026, 9, 15, 23, 59, 59).getTime() / 1000;
        expect(formatTime(NOW)).toBe(new Date(NOW * 1000).toLocaleTimeString());
        expect(formatTime(morning)).toBe(
            new Date(morning * 1000).toLocaleTimeString()
        );
        expect(formatTime(night)).toBe(
            new Date(night * 1000).toLocaleTimeString()
        );
    });

    test("test_format_time_other_day", () => {
        // the other timestamps keep their date, so that a job from
        // yesterday is not taken as one from today
        const yesterday = new Date(2026, 9, 14, 23, 59, 59).getTime() / 1000;
        const tomorrow = new Date(2026, 9, 16, 0, 0, 0).getTime() / 1000;
        const year = new Date(2025, 9, 15, 14, 33, 12).getTime() / 1000;
        expect(formatTime(yesterday)).toBe(
            new Date(yesterday * 1000).toLocaleString()
        );
        expect(formatTime(tomorrow)).toBe(
            new Date(tomorrow * 1000).toLocaleString()
        );
        expect(formatTime(year)).toBe(new Date(year * 1000).toLocaleString());
        expect(formatTime(year)).not.toBe(formatTime(NOW));
    });

    test("test_format_time_missing", () => {
        expect(formatTime(undefined)).toBe("-");
        expect(formatTime(null as unknown as number)).toBe("-");
    });

    test("test_format_duration", () => {
        expect(formatDuration(42)).toBe("42s");
        expect(formatDuration(150)).toBe("2m");
        expect(formatDuration(3600)).toBe("1h");
        expect(formatDuration(8100)).toBe("2h 15m");
        expect(formatDuration(86400)).toBe("1d");
        expect(formatDuration(6 * 86400 + 4 * 3600)).toBe("6d 4h");
        expect(formatDuration(null)).toBe("-");
    });

    test("test_format_relative_time", () => {
        expect(formatRelativeTime(NOW - 10)).toBe("just now");
        expect(formatRelativeTime(NOW - 120)).toBe("2m ago");
        expect(formatRelativeTime(NOW - 3 * 3600)).toBe("3h ago");
        expect(formatRelativeTime(NOW - 2 * 86400)).toBe("2d ago");
        expect(formatRelativeTime(undefined)).toBe("-");
    });
});
