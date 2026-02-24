import React, { FC, FormHTMLAttributes, useMemo } from "react";

import "./form.css";

interface FormProps extends FormHTMLAttributes<HTMLFormElement> {
    style?: string[];
}

export const Form: FC<FormProps> = ({
    style = [],
    children,
    ...rest
}) => {
    const classes = useMemo(
        () => ["form", ...style].filter(Boolean).join(" "),
        [style]
    );
    return (
        <form className={classes} {...rest}>
            {children}
        </form>
    );
};
