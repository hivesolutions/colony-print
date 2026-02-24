import React, { FC, useMemo, HTMLAttributes } from "react";

import "./text.css";

interface TextProps extends HTMLAttributes<HTMLSpanElement> {
    variant?: "default" | "secondary" | "small";
    style?: string[];
}

export const Text: FC<TextProps> = ({
    variant = "default",
    style = [],
    children,
    ...rest
}) => {
    const classes = useMemo(
        () =>
            ["text", `text-${variant}`, ...style]
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
