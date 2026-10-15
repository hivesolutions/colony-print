import { afterEach, beforeEach, describe, expect, test, vi } from "vitest";

import { ColonyPrintAPI } from "../../api/colony-print";

describe("ColonyPrintAPITest", () => {
    let api: ColonyPrintAPI;
    let fetch: ReturnType<typeof vi.fn>;

    beforeEach(() => {
        api = new ColonyPrintAPI({
            baseUrl: "https://print.example.com",
            sessionId: "sid"
        });
        fetch = vi
            .fn()
            .mockResolvedValue(
                new Response(JSON.stringify({ id: "job" }), { status: 200 })
            );
        vi.stubGlobal("fetch", fetch);
    });

    afterEach(() => {
        vi.unstubAllGlobals();
    });

    test("test_list_node_printers", async () => {
        const printers = [
            {
                name: "Receipt",
                engine: "npcolony",
                node_id: "shop-1",
                node_name: "Shop 1",
                last_ping: 100
            }
        ];
        fetch.mockResolvedValue(
            new Response(JSON.stringify(printers), { status: 200 })
        );
        expect(await api.listNodePrinters()).toEqual(printers);
        const [url, options] = fetch.mock.calls[0];
        expect(url).toBe("https://print.example.com/printers/nodes");
        expect(options.method).toBe(undefined);
        expect(options.headers["X-Session-Id"]).toBe("sid");
    });

    test("test_print_node_hello", async () => {
        // the printer is sent as a field, so that any name (e.g., with
        // spaces or the backslashes of a windows network printer) is valid
        expect(
            await api.printNodeHello("shop 1", "\\\\server\\Receipt 80")
        ).toEqual({ id: "job" });
        const [url, options] = fetch.mock.calls[0];
        expect(url).toBe(
            "https://print.example.com/nodes/shop%201/printers/print_hello"
        );
        expect(options.method).toBe("POST");
        expect(options.headers["Content-Type"]).toBe(
            "application/x-www-form-urlencoded"
        );
        expect(options.headers["X-Session-Id"]).toBe("sid");
        expect((options.body as URLSearchParams).get("printer")).toBe(
            "\\\\server\\Receipt 80"
        );
    });

    test("test_print_node_hello_error", async () => {
        fetch.mockResolvedValue(
            new Response("Node not found", { status: 404 })
        );
        await expect(api.printNodeHello("other", "Receipt")).rejects.toThrow(
            "Node not found"
        );
    });
});
