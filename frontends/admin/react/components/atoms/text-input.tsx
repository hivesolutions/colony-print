import React, { FC, useMemo, InputHTMLAttributes } from "react";

import "./text-input.css";

interface TextInputProps extends InputHTMLAttributes<HTMLInputElement> {
    label?: string;
    error?: string;
    style?: string[];
}

export const TextInput: FC<TextInputProps> = ({
    label,
    error,
    style = [],
    id,
    ...rest
}) => {
    const classes = useMemo(
        () =>
            ["text-input", error ? "text-input-error" : "", ...style]
                .filter(Boolean)
                .join(" "),
        [error, style]
    );
    return (
        <div className="text-input-container">
            {label && (
                <label className="text-input-label" htmlFor={id}>
                    {label}
                </label>
            )}
            <input className={classes} id={id} {...rest} />
            {error && <span className="text-input-error-text">{error}</span>}
        </div>
    );
};
