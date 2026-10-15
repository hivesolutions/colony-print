/**
 * The labels of the sections of the admin, by the first
 * segment of their path, as shown in the breadcrumb.
 */
const SECTIONS = new Map([
    ["", "Dashboard"],
    ["nodes", "Nodes"],
    ["jobs", "Jobs"],
    ["printers", "Printers"],
    ["settings", "Settings"]
]);

export interface Breadcrumb {
    label: string;
    path: string;
}

/**
 * Decodes the (URI encoded) segment of a path, keeping it as
 * it is when it's not a valid encoding (e.g., a lone "%").
 */
const decodeSegment = (segment: string): string => {
    try {
        return decodeURIComponent(segment);
    } catch {
        return segment;
    }
};

/**
 * Builds the breadcrumb of the page with the provided path, its
 * section and the identifier of the shown item, if any (e.g.,
 * "/nodes/shop-1" is "Nodes" and "shop-1"), the unknown paths
 * being the dashboard, as they're redirected to it.
 */
export const getBreadcrumbs = (pathname: string): Breadcrumb[] => {
    const [section = "", id] = pathname.split("/").filter(Boolean);
    const label = SECTIONS.get(section);
    if (label === undefined) return [{ label: "Dashboard", path: "/" }];
    const breadcrumbs = [{ label, path: `/${section}` }];
    if (id) {
        breadcrumbs.push({
            label: decodeSegment(id),
            path: `/${section}/${id}`
        });
    }
    return breadcrumbs;
};

/**
 * Finds the page of the node or of the job with the provided
 * identifier (case insensitive), the jobs also being found by
 * the start of their identifier (as the lists shorten it) when
 * only one job starts with it, or the jobs list filtered by it
 * when several do, null when nothing is found.
 */
export const findSearchTarget = (
    query: string,
    nodeIds: string[],
    jobIds: string[]
): string | null => {
    const value = query.trim().toLowerCase();
    if (!value) return null;
    const nodeId = nodeIds.find((id) => id.toLowerCase() === value);
    if (nodeId !== undefined) return `/nodes/${encodeURIComponent(nodeId)}`;
    const matches = jobIds.filter((id) => id.toLowerCase().startsWith(value));
    const jobId =
        matches.find((id) => id.toLowerCase() === value) ??
        (matches.length === 1 ? matches[0] : undefined);
    if (jobId !== undefined) return `/jobs/${encodeURIComponent(jobId)}`;
    if (matches.length > 1) {
        return `/jobs?query=${encodeURIComponent(query.trim())}`;
    }
    return null;
};
