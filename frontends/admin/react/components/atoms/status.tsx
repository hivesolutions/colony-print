import React, { FC, useMemo, HTMLAttributes } from "react";

import "./status.css";

interface StatusProps extends HTMLAttributes<HTMLSpanElement> {
    variant?: "default" | "success" | "error" | "warning" | "info";
    style?: string[];
}

export const Status: FC<StatusProps> = ({
    variant = "default",
    style = [],
    children,
    ...rest
}) => {
    const classes = useMemo(
        () =>
            ["status", `status-${variant}`, ...style]
                .filter(Boolean)
                .join(" "),
        [variant, style]
    );
    return (
        <span className={classes} {...rest}>
            <span className="status-dot" />
            {children}
        </span>
    );
};
