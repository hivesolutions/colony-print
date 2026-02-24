import React, { FC, useMemo, ButtonHTMLAttributes } from "react";

import "./button.css";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
    variant?: "primary" | "secondary" | "danger";
    size?: "sm" | "md" | "lg";
    loading?: boolean;
    style?: string[];
}

export const Button: FC<ButtonProps> = ({
    variant = "primary",
    size = "md",
    loading = false,
    disabled,
    style = [],
    children,
    ...rest
}) => {
    const classes = useMemo(
        () =>
            ["button", `button-${variant}`, `button-${size}`, ...style]
                .filter(Boolean)
                .join(" "),
        [variant, size, style]
    );
    return (
        <button
            className={classes}
            disabled={disabled || loading}
            {...rest}
        >
            {loading ? "Loading..." : children}
        </button>
    );
};
