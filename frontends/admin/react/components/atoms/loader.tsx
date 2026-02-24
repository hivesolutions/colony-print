import React, { FC, useMemo } from "react";

import "./loader.css";

interface LoaderProps {
    size?: "sm" | "md" | "lg";
    style?: string[];
}

export const Loader: FC<LoaderProps> = ({ size = "md", style = [] }) => {
    const classes = useMemo(
        () =>
            ["loader", `loader-${size}`, ...style]
                .filter(Boolean)
                .join(" "),
        [size, style]
    );
    return <div className={classes} />;
};
