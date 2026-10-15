import { describe, expect, test } from "vitest";

import { NodePrinterInfo } from "../../api/colony-print";
import { formatPaper, isNodeDefault } from "../../utils";

const printer: NodePrinterInfo = {
    name: "Receipt 80",
    engine: "npcolony",
    node_id: "shop",
    node_name: "Shop",
    last_ping: null
};

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

    test("test_is_node_default", () => {
        // the printer named by the node is its default one, whatever the
        // case of the name and the default printer of the system
        expect(isNodeDefault({ ...printer, node_printer: "Receipt 80" })).toBe(
            true
        );
        expect(isNodeDefault({ ...printer, node_printer: "RECEIPT 80" })).toBe(
            true
        );
        expect(
            isNodeDefault({
                ...printer,
                node_printer: "office",
                is_default: true
            })
        ).toBe(false);
    });

    test("test_is_node_default_system", () => {
        // the default printer of the system is the one of the nodes that
        // name none (as they do by default) or an invalid one
        expect(
            isNodeDefault({
                ...printer,
                node_printer: "default",
                is_default: true
            })
        ).toBe(true);
        expect(isNodeDefault({ ...printer, node_printer: "default" })).toBe(
            false
        );
        expect(
            isNodeDefault({ ...printer, node_printer: "", is_default: true })
        ).toBe(true);
        expect(
            isNodeDefault({ ...printer, node_printer: null, is_default: true })
        ).toBe(true);
        expect(isNodeDefault({ ...printer, is_default: true })).toBe(true);
        expect(isNodeDefault(printer)).toBe(false);
        expect(
            isNodeDefault({
                ...printer,
                node_printer: 1 as unknown as string,
                is_default: true
            })
        ).toBe(true);
    });
});
