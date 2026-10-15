import { useCallback, useContext } from "react";
import { useNavigate } from "react-router-dom";

import { DataContext } from "../contexts";
import { useAPI } from "./use-api";

export const useLogout = (): (() => Promise<void>) => {
    const api = useAPI();
    const navigate = useNavigate();
    const { setUsername } = useContext(DataContext);

    return useCallback(async () => {
        try {
            await api.logout();
        } catch {
            // ignore logout errors
        }
        localStorage.removeItem("sessionId");
        localStorage.removeItem("username");
        api.sessionId = null;
        api.username = null;
        setUsername(null);
        navigate("/login", { replace: true });
    }, [api, navigate, setUsername]);
};
