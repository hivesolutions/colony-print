import React, { FC, ReactNode, useMemo } from "react";

import "./content.css";

interface ContentProps {
    children: ReactNode;
    style?: string[];
}

export const Content: FC<ContentProps> = ({
    children,
    style = []
}) => {
    const classes = useMemo(
        () => ["content", ...style].filter(Boolean).join(" "),
        [style]
    );
    return <main className={classes}>{children}</main>;
};
