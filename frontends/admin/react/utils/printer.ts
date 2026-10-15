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
