import React, { FC } from "react";
import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";
import {
    act,
    cleanup,
    fireEvent,
    render,
    screen
} from "@testing-library/react";
import {
    MemoryRouter,
    NavigateFunction,
    Route,
    Routes,
    useNavigate
} from "react-router-dom";
import { pulseOutline, syncOutline } from "ionicons/icons";

import { ColonyPrintAPI, NodeInfo } from "../../../../api/colony-print";
import { APIContext } from "../../../../contexts";
import { NodeShow } from "../../../../components/templates/nodes/node-show";

const NOW = Date.now() / 1000;

let navigate: NavigateFunction = () => {};

const MockNavigate: FC = () => {
    navigate = useNavigate();
    return null;
};

const mockNode = (values: Partial<NodeInfo> = {}): NodeInfo =>
    ({
        name: "Shop 1",
        location: "Porto",
        mode: "normal",
        printer: "EPSON TM-T20II",
        engines: ["npcolony", "text"],
        engine_info: {},
        libraries: { npcolony: "1.7.0", appier: "1.34.4" },
        capabilities: ["npcolony", "restart", "update", "auto-update"],
        platform: "win32",
        os: "nt",
        system: {
            name: "Windows",
            release: "10",
            version: "10.0.19045",
            machine: "AMD64",
            architecture: "64bit"
        },
        version: "0.25.0",
        start_time: NOW - 2 * 86400,
        last_ping: NOW - 10,
        update: { auto: true, status: "success", time: NOW - 2 * 86400 },
        stats: {
            total: 41,
            finished: 39,
            error: 1,
            in_flight: 0,
            cancelled: 1,
            last: {
                id: "4f1c9a2e7d",
                name: "FS 2026/1043",
                finish_time: NOW - 60,
                result: "success"
            }
        },
        ...values
    }) as NodeInfo;

describe("NodeShowTest", () => {
    let api: ColonyPrintAPI;

    const renderNode = async (path = "/nodes/shop-1") => {
        const result = render(
            <APIContext.Provider value={api}>
                <MemoryRouter initialEntries={[path]}>
                    <MockNavigate />
                    <Routes>
                        <Route path="/nodes/:id" element={<NodeShow />} />
                    </Routes>
                </MemoryRouter>
            </APIContext.Provider>
        );
        await act(async () => {});
        return result;
    };

    const fields = () =>
        Array.from(
            screen
                .getByRole("heading", { name: "Properties" })
                .closest(".card")!
                .querySelectorAll(".detail-grid-row")
        ).map((row) => [
            row.querySelector("dt")?.textContent,
            row.querySelector("dd")?.textContent
        ]);

    const panel = (name: string) =>
        screen
            .getByRole("heading", { name: name })
            .closest(".card") as HTMLElement;

    beforeEach(() => {
        api = {
            getNode: vi.fn().mockResolvedValue(mockNode()),
            listJobs: vi.fn().mockResolvedValue({}),
            restartNode: vi.fn().mockResolvedValue({}),
            updateNode: vi.fn().mockResolvedValue({}),
            setNodeAutoUpdate: vi.fn().mockResolvedValue({})
        } as unknown as ColonyPrintAPI;
    });

    afterEach(() => {
        cleanup();
        vi.useRealTimers();
        vi.restoreAllMocks();
    });

    test("test_render", async () => {
        const { container } = await renderNode();
        expect(api.getNode).toHaveBeenCalledWith("shop-1");
        expect(screen.getByRole("heading", { name: "Shop 1" }).tagName).toBe(
            "H1"
        );
        expect(container.querySelector(".node-show-id")?.textContent).toBe(
            "shop-1"
        );
        const state = container.querySelector(".node-show-state");
        expect(state?.textContent).toBe("Online, seen just now");
        expect(state?.querySelector(".status")?.className).toBe(
            "status status-success"
        );
        expect(state?.getAttribute("title")).toBe(
            new Date((NOW - 10) * 1000).toLocaleString()
        );
        expect(
            screen.getAllByRole("button").map((button) => button.textContent)
        ).toEqual(["Restart", "Update", "Back to Nodes"]);
        expect(screen.getByRole("button", { name: "Restart" }).className).toBe(
            "button button-secondary button-sm"
        );
        expect(screen.getByRole("button", { name: "Update" }).className).toBe(
            "button button-primary button-sm"
        );
    });

    test("test_render_state", async () => {
        // an offline node that never reported is shown without the
        // time it was last seen at
        api.getNode = vi
            .fn()
            .mockResolvedValue(
                mockNode({ last_ping: undefined, capabilities: [] })
            );
        const { container } = await renderNode();
        const state = container.querySelector(".node-show-state");
        expect(state?.textContent).toBe("Offline");
        expect(state?.querySelector(".status")?.className).toBe(
            "status status-default"
        );
        expect(
            screen.getAllByRole("button").map((button) => button.textContent)
        ).toEqual(["Back to Nodes"]);
    });

    test("test_render_stats", async () => {
        const { container } = await renderNode();
        const cards = Array.from(
            container.querySelectorAll(".node-show-stats .stat-card")
        );
        expect(
            cards.map((card) => [
                card.querySelector(".stat-card-label")?.textContent,
                card.querySelector(".stat-card-value")?.textContent,
                card.className
            ])
        ).toEqual([
            ["Total jobs", "41", "card stat-card"],
            ["Finished", "39", "card stat-card node-show-stat-success"],
            ["Errored", "1", "card stat-card node-show-stat-error"],
            ["In flight", "0", "card stat-card"]
        ]);
    });

    test("test_render_stats_empty", async () => {
        api.getNode = vi.fn().mockResolvedValue(
            mockNode({
                stats: {
                    total: 0,
                    finished: 0,
                    error: 0,
                    in_flight: 0,
                    cancelled: 0
                }
            })
        );
        const { container } = await renderNode();
        expect(
            Array.from(
                container.querySelectorAll(".node-show-stats .stat-card")
            ).map((card) => card.className)
        ).toEqual([
            "card stat-card",
            "card stat-card",
            "card stat-card",
            "card stat-card"
        ]);
        expect(panel("Last Job").textContent).toContain("No jobs printed yet");
    });

    test("test_render_fields", async () => {
        const { container } = await renderNode();
        const started = new Date((NOW - 2 * 86400) * 1000).toLocaleString();
        expect(fields()).toEqual([
            ["Location", "Porto"],
            ["Mode", "normal"],
            ["Printer", "EPSON TM-T20II"],
            ["Engines", "npcolony, text"],
            ["Platform", "win32"],
            ["OS", "nt"],
            ["System", "Windows 10"],
            ["System Version", "10.0.19045"],
            ["Architecture", "AMD64 (64bit)"],
            ["Version", "0.25.0"],
            ["Started", `${started} (2d ago)`]
        ]);
        expect(
            screen.getByRole("heading", { name: "Properties" })
        ).toBeTruthy();
        expect(container.querySelector(".detail-grid .tag")?.className).toBe(
            "tag tag-default"
        );
    });

    test("test_render_fields_missing", async () => {
        // the node of an older version reports less, the missing
        // fields being shown as so
        api.getNode = vi.fn().mockResolvedValue(
            mockNode({
                mode: "email",
                location: "",
                printer: "",
                engines: undefined,
                platform: "",
                os: "",
                version: "",
                start_time: undefined,
                system: {
                    name: "Linux",
                    release: "",
                    version: "",
                    machine: "",
                    architecture: "",
                    distribution: "Ubuntu 24.04 LTS"
                }
            } as unknown as Partial<NodeInfo>)
        );
        const { container } = await renderNode();
        expect(fields()).toEqual([
            ["Location", "-"],
            ["Mode", "email"],
            ["Printer", "-"],
            ["Engines", "-"],
            ["Platform", "-"],
            ["OS", "-"],
            ["System", "Linux"],
            ["Distribution", "Ubuntu 24.04 LTS"],
            ["System Version", "-"],
            ["Architecture", "-"],
            ["Version", "-"],
            ["Started", "-"]
        ]);
        expect(container.querySelector(".detail-grid .tag")?.className).toBe(
            "tag tag-warning"
        );
        cleanup();

        api.getNode = vi
            .fn()
            .mockResolvedValue(
                mockNode({ system: undefined, start_time: undefined })
            );
        await renderNode();
        expect(fields().map(([label]) => label)).toEqual([
            "Location",
            "Mode",
            "Printer",
            "Engines",
            "Platform",
            "OS",
            "Version",
            "Started"
        ]);
    });

    test("test_render_fonts", async () => {
        api.getNode = vi.fn().mockResolvedValue(
            mockNode({
                fonts: [
                    {
                        name: "2 of 5",
                        style: "bold_italic",
                        md5: "9e107d9d",
                        url: "https://fonts.example.com/2of5.ttf",
                        size: 18534,
                        time: NOW - 3 * 86400,
                        active: true
                    },
                    {
                        name: "Carlito",
                        style: "regular",
                        md5: "e4d909c2",
                        size: 636314,
                        time: NOW - 3 * 86400,
                        active: false
                    }
                ]
            })
        );
        await renderNode();
        const fonts = panel("Fonts");
        expect(
            Array.from(fonts.querySelectorAll("th")).map((th) => th.textContent)
        ).toEqual([
            "Name",
            "Style",
            "MD5",
            "URL",
            "Size",
            "Installed",
            "Active"
        ]);
        expect(
            Array.from(fonts.querySelectorAll("tbody tr")).map((row) =>
                Array.from(row.querySelectorAll("td")).map(
                    (td) => td.textContent
                )
            )
        ).toEqual([
            [
                "2 of 5",
                "bold italic",
                "9e107d9d",
                "https://fonts.example.com/2of5.ttf",
                "18.1 KB",
                "3d ago",
                "Yes"
            ],
            ["Carlito", "regular", "e4d909c2", "-", "621.4 KB", "3d ago", "No"]
        ]);
        expect(
            Array.from(fonts.querySelectorAll("tbody .status")).map(
                (status) => status.className
            )
        ).toEqual(["status status-success", "status status-default"]);
    });

    test("test_render_fonts_empty", async () => {
        // the nodes that can install fonts show them, even if none
        api.getNode = vi.fn().mockResolvedValue(
            mockNode({
                capabilities: ["npcolony", "dynamic-fonts"],
                fonts: []
            })
        );
        await renderNode();
        expect(screen.getByText("No fonts installed")).toBeTruthy();
        cleanup();

        // while the other ones don't show the fonts at all
        api.getNode = vi.fn().mockResolvedValue(mockNode());
        await renderNode();
        expect(screen.queryByRole("heading", { name: "Fonts" })).toBe(null);
    });

    test("test_render_engines", async () => {
        api.getNode = vi.fn().mockResolvedValue(
            mockNode({
                engine_info: {
                    npcolony: {
                        version: "1.7.0",
                        printers: [
                            { name: "EPSON", is_default: true, media: "" },
                            { name: "PDF", is_default: false, media: null }
                        ],
                        names: ["a", "b"],
                        empty: []
                    } as unknown as Record<string, string>
                }
            })
        );
        await renderNode();
        const engine = screen
            .getByRole("heading", { name: "Npcolony Engine" })
            .closest(".node-show-section") as HTMLElement;
        expect(
            Array.from(engine.querySelectorAll(".detail-grid-row")).map(
                (row) => row.textContent
            )
        ).toEqual(["version1.7.0"]);

        // only the lists of objects are shown, as tables
        expect(
            Array.from(engine.querySelectorAll(".panel-title")).map(
                (title) => title.textContent
            )
        ).toEqual(["Npcolony Engine", "printers"]);
        const printers = engine.querySelector(".data-table") as HTMLElement;
        expect(
            Array.from(printers.querySelectorAll("th")).map(
                (th) => th.textContent
            )
        ).toEqual(["Name", "Is default", "Media"]);
        expect(
            Array.from(printers.querySelectorAll("tbody tr")).map((row) =>
                Array.from(row.querySelectorAll("td")).map(
                    (td) => td.textContent
                )
            )
        ).toEqual([
            ["EPSON", "Yes", "-"],
            ["PDF", "No", "-"]
        ]);
        expect(
            Array.from(printers.querySelectorAll(".status")).map(
                (status) => status.className
            )
        ).toEqual(["status status-success", "status status-error"]);
    });

    test("test_render_libraries", async () => {
        await renderNode();
        expect(
            Array.from(
                panel("Libraries").querySelectorAll(".node-show-row")
            ).map((row) => row.textContent)
        ).toEqual(["npcolony1.7.0", "appier1.34.4"]);
        cleanup();

        api.getNode = vi.fn().mockResolvedValue(mockNode({ libraries: {} }));
        await renderNode();
        expect(panel("Libraries").textContent).toBe("LibrariesNo libraries");
        cleanup();

        api.getNode = vi
            .fn()
            .mockResolvedValue(mockNode({ libraries: undefined }));
        await renderNode();
        expect(screen.queryByRole("heading", { name: "Libraries" })).toBe(null);
    });

    test("test_render_update", async () => {
        await renderNode();
        const updates = panel("Updates");
        expect(
            updates.querySelector(".panel-title ion-icon")?.getAttribute("icon")
        ).toBe(syncOutline);
        const control = screen.getByRole("switch", { name: "Auto-update" });
        expect(control.getAttribute("aria-checked")).toBe("true");
        expect((control as HTMLButtonElement).disabled).toBe(false);
        expect(updates.textContent).toContain(
            "Enabled, on every start of the node"
        );
        expect(updates.textContent).toContain("Last update2d ago");
        expect(updates.querySelector(".status")?.className).toBe(
            "status status-success"
        );
        expect(updates.querySelector(".node-show-error")).toBe(null);
    });

    test("test_render_update_failure", async () => {
        // the update that failed shows its error, while the nodes
        // without the auto-update capability can't change it
        api.getNode = vi.fn().mockResolvedValue(
            mockNode({
                capabilities: [],
                update: {
                    auto: false,
                    status: "failure",
                    time: null,
                    error: "No network"
                }
            })
        );
        await renderNode();
        const updates = panel("Updates");
        const control = screen.getByRole("switch", { name: "Auto-update" });
        expect(control.getAttribute("aria-checked")).toBe("false");
        expect((control as HTMLButtonElement).disabled).toBe(true);
        expect(updates.textContent).toContain("Disabled");
        expect(updates.textContent).toContain("Last update-");
        expect(updates.querySelector(".status")?.className).toBe(
            "status status-error"
        );
        expect(updates.querySelector(".node-show-error")?.textContent).toBe(
            "No network"
        );
    });

    test("test_render_update_status", async () => {
        api.getNode = vi
            .fn()
            .mockResolvedValue(
                mockNode({ update: { auto: true, status: "running" } })
            );
        await renderNode();
        expect(panel("Updates").querySelector(".status")?.className).toBe(
            "status status-default"
        );
        cleanup();

        api.getNode = vi
            .fn()
            .mockResolvedValue(mockNode({ update: { auto: true } }));
        await renderNode();
        expect(panel("Updates").querySelector(".status")).toBe(null);
        cleanup();

        api.getNode = vi.fn().mockResolvedValue(mockNode({ update: null }));
        await renderNode();
        expect(screen.queryByRole("heading", { name: "Updates" })).toBe(null);
    });

    test("test_render_last", async () => {
        await renderNode();
        const last = panel("Last Job");
        expect(
            last.querySelector(".panel-title ion-icon")?.getAttribute("icon")
        ).toBe(pulseOutline);
        expect(
            screen
                .getByRole("link", { name: "FS 2026/1043" })
                .getAttribute("href")
        ).toBe("/jobs/4f1c9a2e7d");
        expect(last.querySelector(".node-show-muted")?.textContent).toBe(
            "1m ago"
        );
        expect(last.querySelector(".status")?.className).toBe(
            "status status-success"
        );
    });

    test("test_render_last_result", async () => {
        const stats = mockNode().stats!;
        for (const [result, variant] of [
            ["error", "status status-error"],
            ["unknown", "status status-default"]
        ]) {
            api.getNode = vi.fn().mockResolvedValue(
                mockNode({
                    stats: {
                        ...stats,
                        last: { ...stats.last!, result: result }
                    }
                })
            );
            await renderNode();
            expect(panel("Last Job").querySelector(".status")?.className).toBe(
                variant
            );
            cleanup();
        }

        // the last job without a name is shown by its identifier,
        // and without a result when it has none
        api.getNode = vi.fn().mockResolvedValue(
            mockNode({
                stats: {
                    ...stats,
                    last: { id: "4f1c9a2e7d", name: "", finish_time: NOW }
                }
            })
        );
        await renderNode();
        expect(screen.getByRole("link", { name: "4f1c9a2e7d" })).toBeTruthy();
        expect(panel("Last Job").querySelector(".status")).toBe(null);
    });

    test("test_render_capabilities", async () => {
        await renderNode();
        const capabilities = panel("Capabilities");
        expect(capabilities.querySelector(".panel-actions")?.textContent).toBe(
            "4"
        );
        expect(
            Array.from(capabilities.querySelectorAll(".tag")).map((tag) => [
                tag.textContent,
                tag.className
            ])
        ).toEqual([
            ["npcolony", "tag tag-default node-show-capability"],
            ["restart", "tag tag-default node-show-capability"],
            ["update", "tag tag-default node-show-capability"],
            ["auto-update", "tag tag-default node-show-capability"]
        ]);
        cleanup();

        api.getNode = vi
            .fn()
            .mockResolvedValue(mockNode({ capabilities: undefined }));
        await renderNode();
        expect(panel("Capabilities").textContent).toBe(
            "Capabilities0No capabilities reported"
        );
    });

    test("test_render_error", async () => {
        api.getNode = vi.fn().mockRejectedValue(new Error("Not found"));
        const { container } = await renderNode();
        expect(screen.getByRole("heading", { name: "Node" })).toBeTruthy();
        expect(container.querySelector(".node-show-id")?.textContent).toBe(
            "shop-1"
        );
        expect(container.querySelector(".node-show-state")).toBe(null);
        expect(fields()).toEqual([]);
        expect(
            container.querySelector(".node-show-side")?.children.length
        ).toBe(0);
    });

    test("test_render_loading", () => {
        api.getNode = vi.fn().mockReturnValue(new Promise(() => {}));
        const { container } = render(
            <APIContext.Provider value={api}>
                <MemoryRouter initialEntries={["/nodes/shop-1"]}>
                    <Routes>
                        <Route path="/nodes/:id" element={<NodeShow />} />
                    </Routes>
                </MemoryRouter>
            </APIContext.Provider>
        );
        expect(container.querySelector(".loader")).toBeTruthy();
        expect(api.listJobs).not.toHaveBeenCalled();
    });

    test("test_pending", async () => {
        vi.useFakeTimers();
        api.listJobs = vi.fn().mockResolvedValue({
            other: {
                id: "other",
                node_id: "shop-2",
                type: "update",
                status: "queued"
            },
            done: {
                id: "done",
                node_id: "shop-1",
                type: "update",
                status: "finished"
            },
            job: {
                id: "job",
                node_id: "shop-1",
                type: "update",
                status: "printing"
            }
        });
        await renderNode();
        const button = screen.getByRole("button", {
            name: "Updating..."
        }) as HTMLButtonElement;
        expect(button.disabled).toBe(true);
        expect(screen.queryByRole("button", { name: "Restart" })).toBe(null);
        expect(api.getNode).toHaveBeenCalledTimes(1);

        // the node is refreshed (silently) while the job is pending,
        // until it's done, showing the actions again
        await act(async () => {
            await vi.advanceTimersByTimeAsync(3000);
        });
        expect(api.getNode).toHaveBeenCalledTimes(2);
        expect(document.querySelector(".loader")).toBe(null);

        api.listJobs = vi.fn().mockResolvedValue({});
        await act(async () => {
            await vi.advanceTimersByTimeAsync(3000);
        });
        expect(api.getNode).toHaveBeenCalledTimes(3);
        expect(screen.getByRole("button", { name: "Restart" })).toBeTruthy();

        await act(async () => {
            await vi.advanceTimersByTimeAsync(9000);
        });
        expect(api.getNode).toHaveBeenCalledTimes(3);
    });

    test("test_pending_restart", async () => {
        api.listJobs = vi.fn().mockResolvedValue({
            job: {
                id: "job",
                node_id: "shop-1",
                type: "restart",
                status: "queued"
            }
        });
        await renderNode();
        expect(
            screen.getByRole("button", { name: "Restarting..." })
        ).toBeTruthy();
    });

    test("test_pending_error", async () => {
        // the node is shown when its jobs can't be listed, as with
        // no restart pending
        api.listJobs = vi.fn().mockRejectedValue(new Error("Offline"));
        await renderNode();
        expect(screen.getByRole("button", { name: "Restart" })).toBeTruthy();
    });

    test("test_restart", async () => {
        const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
        await renderNode();
        await act(async () => {
            fireEvent.click(screen.getByRole("button", { name: "Restart" }));
        });
        expect(confirm).toHaveBeenCalledWith(
            "Restart the node shop-1? The node is restarted once its pending jobs are printed."
        );
        expect(api.restartNode).toHaveBeenCalledWith("shop-1");
        expect(api.updateNode).not.toHaveBeenCalled();
        expect(api.getNode).toHaveBeenCalledTimes(2);
        expect(
            (
                screen.getByRole("button", {
                    name: "Restart"
                }) as HTMLButtonElement
            ).disabled
        ).toBe(false);
    });

    test("test_restart_update", async () => {
        const confirm = vi.spyOn(window, "confirm").mockReturnValue(true);
        await renderNode();
        await act(async () => {
            fireEvent.click(screen.getByRole("button", { name: "Update" }));
        });
        expect(confirm).toHaveBeenCalledWith(
            "Update the node shop-1? The node is restarted and updates its packages on the way up."
        );
        expect(api.updateNode).toHaveBeenCalledWith("shop-1");
        expect(api.restartNode).not.toHaveBeenCalled();
    });

    test("test_restart_cancel", async () => {
        vi.spyOn(window, "confirm").mockReturnValue(false);
        await renderNode();
        await act(async () => {
            fireEvent.click(screen.getByRole("button", { name: "Restart" }));
        });
        expect(api.restartNode).not.toHaveBeenCalled();
        expect(api.getNode).toHaveBeenCalledTimes(1);
    });

    test("test_restart_error", async () => {
        // the error is ignored, as the node is refreshed anyway and
        // shows its actual state
        vi.spyOn(window, "confirm").mockReturnValue(true);
        api.restartNode = vi.fn().mockRejectedValue(new Error("Offline"));
        await renderNode();
        await act(async () => {
            fireEvent.click(screen.getByRole("button", { name: "Restart" }));
        });
        expect(api.getNode).toHaveBeenCalledTimes(2);
        expect(screen.getByRole("button", { name: "Restart" })).toBeTruthy();
    });

    test("test_auto_update", async () => {
        vi.useFakeTimers();
        await renderNode();
        api.getNode = vi
            .fn()
            .mockResolvedValueOnce(mockNode())
            .mockResolvedValue(
                mockNode({ update: { auto: false, status: "success" } })
            );
        await act(async () => {
            fireEvent.click(
                screen.getByRole("switch", { name: "Auto-update" })
            );
        });
        expect(api.setNodeAutoUpdate).toHaveBeenCalledWith("shop-1", false);
        expect((screen.getByRole("switch") as HTMLButtonElement).disabled).toBe(
            true
        );

        // the node is polled until it reports the change
        await act(async () => {
            await vi.advanceTimersByTimeAsync(1000);
        });
        expect(api.getNode).toHaveBeenCalledTimes(1);
        expect(screen.getByRole("switch").getAttribute("aria-checked")).toBe(
            "true"
        );
        await act(async () => {
            await vi.advanceTimersByTimeAsync(1000);
        });
        expect(api.getNode).toHaveBeenCalledTimes(2);
        expect(screen.getByRole("switch").getAttribute("aria-checked")).toBe(
            "false"
        );
        expect((screen.getByRole("switch") as HTMLButtonElement).disabled).toBe(
            false
        );

        await act(async () => {
            await vi.advanceTimersByTimeAsync(10000);
        });
        expect(api.getNode).toHaveBeenCalledTimes(2);
    });

    test("test_auto_update_timeout", async () => {
        // the node that never reports the change is polled for ten
        // seconds, being shown with its (reported) state afterwards
        vi.useFakeTimers();
        await renderNode();
        api.getNode = vi.fn().mockResolvedValue(mockNode());
        await act(async () => {
            fireEvent.click(
                screen.getByRole("switch", { name: "Auto-update" })
            );
        });
        await act(async () => {
            await vi.advanceTimersByTimeAsync(20000);
        });
        expect(api.getNode).toHaveBeenCalledTimes(10);
        expect(screen.getByRole("switch").getAttribute("aria-checked")).toBe(
            "true"
        );
        expect((screen.getByRole("switch") as HTMLButtonElement).disabled).toBe(
            false
        );
    });

    test("test_auto_update_error", async () => {
        api.setNodeAutoUpdate = vi.fn().mockRejectedValue(new Error("Offline"));
        await renderNode();
        await act(async () => {
            fireEvent.click(
                screen.getByRole("switch", { name: "Auto-update" })
            );
        });
        expect(api.getNode).toHaveBeenCalledTimes(1);
        expect(screen.getByRole("switch").getAttribute("aria-checked")).toBe(
            "true"
        );
        expect((screen.getByRole("switch") as HTMLButtonElement).disabled).toBe(
            false
        );
    });

    test("test_auto_update_unmount", async () => {
        // the polling stops once the node is not shown anymore
        vi.useFakeTimers();
        await renderNode();
        await act(async () => {
            fireEvent.click(
                screen.getByRole("switch", { name: "Auto-update" })
            );
        });
        cleanup();
        await act(async () => {
            await vi.advanceTimersByTimeAsync(20000);
        });
        expect(api.getNode).toHaveBeenCalledTimes(1);
    });

    test("test_auto_update_navigate", async () => {
        // the node shown after navigating is not changed by the
        // polling of the previous one, that is stopped
        vi.useFakeTimers();
        let resolve: (value: unknown) => void = () => {};
        await renderNode();
        api.getNode = vi
            .fn()
            .mockReturnValueOnce(new Promise((r) => (resolve = r)))
            .mockResolvedValue(mockNode({ name: "Shop 2" }));
        await act(async () => {
            fireEvent.click(
                screen.getByRole("switch", { name: "Auto-update" })
            );
        });
        await act(async () => {
            await vi.advanceTimersByTimeAsync(1000);
        });
        await act(async () => {
            navigate("/nodes/shop-2");
        });
        expect(screen.getByRole("heading", { name: "Shop 2" })).toBeTruthy();
        await act(async () => {
            resolve(mockNode({ name: "Stale" }));
        });
        expect(screen.getByRole("heading", { name: "Shop 2" })).toBeTruthy();
        expect(screen.queryByRole("heading", { name: "Stale" })).toBe(null);
    });

    test("test_navigate", async () => {
        // the responses for the node shown before are ignored, when
        // they arrive after the one of the node shown now
        let resolveNode: (value: unknown) => void = () => {};
        api.getNode = vi
            .fn()
            .mockReturnValueOnce(new Promise((r) => (resolveNode = r)))
            .mockResolvedValue(mockNode({ name: "Shop 2" }));
        await renderNode();
        await act(async () => {
            navigate("/nodes/shop-2");
        });
        expect(screen.getByRole("heading", { name: "Shop 2" })).toBeTruthy();
        await act(async () => {
            resolveNode(mockNode({ name: "Stale" }));
        });
        expect(screen.getByRole("heading", { name: "Shop 2" })).toBeTruthy();
        expect(document.querySelector(".loader")).toBe(null);
        cleanup();

        // as well as the errors of the node before
        api.getNode = vi
            .fn()
            .mockReturnValueOnce(new Promise((_, r) => (resolveNode = r)))
            .mockResolvedValue(mockNode({ name: "Shop 2" }));
        await renderNode();
        await act(async () => {
            navigate("/nodes/shop-2");
        });
        await act(async () => {
            resolveNode(new Error("Not found"));
        });
        expect(screen.getByRole("heading", { name: "Shop 2" })).toBeTruthy();
    });

    test("test_navigate_jobs", async () => {
        // the jobs (and their errors) of the node shown before are
        // ignored, not showing its restart as the one of this node
        let resolveJobs: (value: unknown) => void = () => {};
        let rejectJobs: (value: unknown) => void = () => {};
        api.listJobs = vi
            .fn()
            .mockReturnValueOnce(new Promise((r) => (resolveJobs = r)))
            .mockReturnValueOnce(new Promise((_, r) => (rejectJobs = r)))
            .mockResolvedValue({});
        await renderNode();
        await act(async () => {
            navigate("/nodes/shop-2");
        });
        await act(async () => {
            navigate("/nodes/shop-3");
        });
        await act(async () => {
            resolveJobs({
                job: {
                    id: "job",
                    node_id: "shop-1",
                    type: "restart",
                    status: "queued"
                }
            });
            rejectJobs(new Error("Offline"));
        });
        expect(screen.queryByRole("button", { name: "Restarting..." })).toBe(
            null
        );
        expect(screen.getByRole("button", { name: "Restart" })).toBeTruthy();
    });

    test("test_back", async () => {
        const back = vi
            .spyOn(window.history, "back")
            .mockImplementation(() => {});
        await renderNode();
        fireEvent.click(screen.getByRole("button", { name: "Back to Nodes" }));
        expect(back).toHaveBeenCalledTimes(1);
    });
});
