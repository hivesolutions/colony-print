import React, { FC, useMemo, LabelHTMLAttributes } from "react";

import "./label.css";

interface LabelProps extends LabelHTMLAttributes<HTMLLabelElement> {
    style?: string[];
}

export const Label: FC<LabelProps> = ({
    style = [],
    children,
    ...rest
}) => {
    const classes = useMemo(
        () => ["label", ...style].filter(Boolean).join(" "),
        [style]
    );
    return (
        <label className={classes} {...rest}>
            {children}
        </label>
    );
};
