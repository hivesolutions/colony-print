import { NodePrinterInfo } from "../api/colony-print";

/**
 * Formats the size of the paper of a printer, its width and length
 * in points (as reported by npcolony), in millimeters rounded to
 * the millimeter (e.g., "80 × 297 mm"), "-" when either is missing.
 */
export const formatPaper = (
    width?: number | null,
    length?: number | null
): string => {
    if (!width || !length) return "-";
    const millimeters = (points: number) => Math.round((points * 25.4) / 72);
    return `${millimeters(width)} × ${millimeters(length)} mm`;
};

/**
 * Checks if the printer is the default one of its node, the
 * one that prints the jobs of the node that select none: the
 * printer named by the node (its `NODE_PRINTER`, the case being
 * ignored as the node does) or the default one of the system
 * when it names none (or "default", its value when the node
 * is not configured).
 */
export const isNodeDefault = (printer: NodePrinterInfo): boolean => {
    const name = printer.node_printer;
    if (typeof name !== "string" || ["", "default"].includes(name))
        return Boolean(printer.is_default);
    return printer.name.toLowerCase() === name.toLowerCase();
};
