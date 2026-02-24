import React, { FC, useMemo } from "react";

import "./separator.css";

interface SeparatorProps {
    style?: string[];
}

export const Separator: FC<SeparatorProps> = ({ style = [] }) => {
    const classes = useMemo(
        () => ["separator", ...style].filter(Boolean).join(" "),
        [style]
    );
    return <hr className={classes} />;
};
