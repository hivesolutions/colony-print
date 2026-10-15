import React, { FC, ReactNode } from "react";
import {
    Mock,
    afterEach,
    beforeEach,
    describe,
    expect,
    test,
    vi
} from "vitest";
import { act, cleanup, renderHook } from "@testing-library/react";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";

import { ColonyPrintAPI } from "../../api/colony-print";
import { APIContext, DataContext } from "../../contexts";
import { useLogout } from "../../hooks";

let location = "";

const MockLocation: FC = () => {
    location = useLocation().pathname;
    return null;
};

describe("UseLogoutTest", () => {
    let api: ColonyPrintAPI;
    let setUsername: Mock<(username: string | null) => void>;
    let wrapper: FC<{ children: ReactNode }>;

    beforeEach(() => {
        location = "";
        api = new ColonyPrintAPI({ sessionId: "sid", username: "admin" });
        api.logout = vi.fn().mockResolvedValue(undefined);
        setUsername = vi.fn<(username: string | null) => void>();
        localStorage.setItem("sessionId", "sid");
        localStorage.setItem("username", "admin");
        localStorage.setItem("baseUrl", "https://print.example.com");
        wrapper = ({ children }) => (
            <APIContext.Provider value={api}>
                <DataContext.Provider
                    value={{ username: "admin", setUsername }}
                >
                    <MemoryRouter initialEntries={["/settings"]}>
                        <Routes>
                            <Route path="*" element={<MockLocation />} />
                        </Routes>
                        {children}
                    </MemoryRouter>
                </DataContext.Provider>
            </APIContext.Provider>
        );
    });

    afterEach(() => {
        cleanup();
        localStorage.clear();
    });

    test("test_use_logout", async () => {
        const { result } = renderHook(() => useLogout(), { wrapper });
        expect(location).toBe("/settings");

        await act(async () => {
            await result.current();
        });

        expect(api.logout).toHaveBeenCalledTimes(1);
        expect(api.sessionId).toBe(null);
        expect(api.username).toBe(null);
        expect(localStorage.getItem("sessionId")).toBe(null);
        expect(localStorage.getItem("username")).toBe(null);
        expect(localStorage.getItem("baseUrl")).toBe(
            "https://print.example.com"
        );
        expect(setUsername).toHaveBeenCalledWith(null);
        expect(location).toBe("/login");
    });

    test("test_use_logout_error", async () => {
        // the session is dropped by the admin even when the server
        // can't be reached to drop it (e.g., while it's offline)
        api.logout = vi.fn().mockRejectedValue(new Error("Offline"));
        const { result } = renderHook(() => useLogout(), { wrapper });

        await act(async () => {
            await result.current();
        });

        expect(api.sessionId).toBe(null);
        expect(localStorage.getItem("sessionId")).toBe(null);
        expect(setUsername).toHaveBeenCalledWith(null);
        expect(location).toBe("/login");
    });
});
