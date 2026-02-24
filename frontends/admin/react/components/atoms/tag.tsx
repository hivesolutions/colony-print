import React, { FC, useMemo, HTMLAttributes } from "react";

import "./tag.css";

interface TagProps extends HTMLAttributes<HTMLSpanElement> {
    variant?: "default" | "success" | "error" | "warning";
    style?: string[];
}

export const Tag: FC<TagProps> = ({
    variant = "default",
    style = [],
    children,
    ...rest
}) => {
    const classes = useMemo(
        () =>
            ["tag", `tag-${variant}`, ...style]
                .filter(Boolean)
                .join(" "),
        [variant, style]
    );
    return (
        <span className={classes} {...rest}>
            {children}
        </span>
    );
};
