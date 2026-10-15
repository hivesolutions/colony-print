import { describe, expect, test } from "vitest";

import { formatPaper } from "../../utils";

describe("PrinterTest", () => {
    test("test_format_paper", () => {
        // the sizes are in points, as reported by npcolony, rounded to
        // the millimeter (an 80 mm roll, an A4 sheet and a 4 x 6 label)
        expect(formatPaper(226.77, 841.89)).toBe("80 × 297 mm");
        expect(formatPaper(595.28, 841.89)).toBe("210 × 297 mm");
        expect(formatPaper(288, 432)).toBe("102 × 152 mm");
        expect(formatPaper(841.89, 595.28)).toBe("297 × 210 mm");
    });

    test("test_format_paper_missing", () => {
        // the printers that report no size (e.g., an engraver) have none
        expect(formatPaper(undefined, undefined)).toBe("-");
        expect(formatPaper(226.77, undefined)).toBe("-");
        expect(formatPaper(undefined, 841.89)).toBe("-");
        expect(formatPaper(null, null)).toBe("-");
        expect(formatPaper(0, 841.89)).toBe("-");
    });
});
