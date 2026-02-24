import React, { FC, ReactNode } from "react";
import { Navigate } from "react-router-dom";

import { useAPI } from "../../hooks";

interface ProtectedRouteProps {
    children: ReactNode;
}

export const ProtectedRoute: FC<ProtectedRouteProps> = ({
    children
}) => {
    const api = useAPI();
    if (!api.sessionId) {
        return <Navigate to="/login" replace />;
    }
    return <>{children}</>;
};
