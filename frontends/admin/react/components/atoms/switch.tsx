import React, { FC, useMemo, ButtonHTMLAttributes } from "react";

import "./switch.css";

interface SwitchProps
    extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "onChange"> {
    checked?: boolean;
    onChange?: (checked: boolean) => void;
    style?: string[];
}

export const Switch: FC<SwitchProps> = ({
    checked = false,
    onChange,
    style = [],
    ...rest
}) => {
    const classes = useMemo(
        () =>
            ["switch", checked ? "switch-checked" : "", ...style]
                .filter(Boolean)
                .join(" "),
        [checked, style]
    );
    return (
        <button
            type="button"
            role="switch"
            className={classes}
            aria-checked={checked}
            onClick={() => onChange?.(!checked)}
            {...rest}
        >
            <span className="switch-thumb" />
        </button>
    );
};
