import React, { FC, useCallback, useEffect, useState } from "react";
import {
    BrowserRouter,
    Routes,
    Route,
    Navigate,
    useLocation
} from "react-router-dom";

import { ColonyPrintAPI } from "./api/colony-print";
import { APIContext, DataContext } from "./contexts";
import { TopBar, SideBar, Content, ProtectedRoute } from "./components/molecules";
import { Login } from "./components/templates/login/login";
import { Dashboard } from "./components/templates/dashboard/dashboard";
import { NodesList } from "./components/templates/nodes/nodes-list";
import { NodeShow } from "./components/templates/nodes/node-show";
import { JobsList } from "./components/templates/jobs/jobs-list";
import { JobShow } from "./components/templates/jobs/job-show";
import { PrintersList } from "./components/templates/printers/printers-list";
import { Settings } from "./components/templates/settings/settings";

import "./app.css";

export const App: FC = () => {
    const [api] = useState<ColonyPrintAPI>(
        () =>
            new ColonyPrintAPI({
                baseUrl: localStorage.getItem("baseUrl") ?? "",
                sessionId: localStorage.getItem("sessionId"),
                username: localStorage.getItem("username")
            })
    );
    const [username, setUsername] = useState<string | null>(
        localStorage.getItem("username")
    );

    return (
        <APIContext.Provider value={api}>
            <DataContext.Provider value={{ username, setUsername }}>
                <BrowserRouter
                    basename={
                        window.location.pathname.startsWith("/admin-ui")
                            ? "/admin-ui"
                            : "/"
                    }
                >
                    <Routes>
                        <Route
                            path="/login"
                            element={<Login />}
                        />
                        <Route
                            path="/*"
                            element={
                                <ProtectedRoute>
                                    <Layout />
                                </ProtectedRoute>
                            }
                        />
                    </Routes>
                </BrowserRouter>
            </DataContext.Provider>
        </APIContext.Provider>
    );
};

const Layout: FC = () => {
    const location = useLocation();
    const [sidebarOpen, setSidebarOpen] = useState(false);

    const toggleSidebar = useCallback(
        () => setSidebarOpen((prev) => !prev),
        []
    );
    const closeSidebar = useCallback(() => setSidebarOpen(false), []);

    useEffect(() => {
        setSidebarOpen(false);
    }, [location.pathname]);

    return (
        <div className="layout">
            <TopBar onToggleSidebar={toggleSidebar} />
            <div className="layout-body">
                {sidebarOpen && (
                    <div
                        className="layout-overlay"
                        onClick={closeSidebar}
                    />
                )}
                <SideBar open={sidebarOpen} onClose={closeSidebar} />
                <Content>
                    <Routes>
                        <Route path="/" element={<Dashboard />} />
                        <Route path="/nodes" element={<NodesList />} />
                        <Route
                            path="/nodes/:id"
                            element={<NodeShow />}
                        />
                        <Route path="/jobs" element={<JobsList />} />
                        <Route
                            path="/jobs/:id"
                            element={<JobShow />}
                        />
                        <Route
                            path="/printers"
                            element={<PrintersList />}
                        />
                        <Route
                            path="/settings"
                            element={<Settings />}
                        />
                        <Route
                            path="*"
                            element={<Navigate to="/" replace />}
                        />
                    </Routes>
                </Content>
            </div>
        </div>
    );
};
