import React, { FC, useMemo } from "react";
import {
    Link as RouterLink,
    LinkProps as RouterLinkProps
} from "react-router-dom";

import "./link.css";

interface LinkProps extends RouterLinkProps {
    style?: string[];
}

export const Link: FC<LinkProps> = ({
    style = [],
    children,
    ...rest
}) => {
    const classes = useMemo(
        () => ["link", ...style].filter(Boolean).join(" "),
        [style]
    );
    return (
        <RouterLink className={classes} {...rest}>
            {children}
        </RouterLink>
    );
};
