import React, { FC, useMemo, HTMLAttributes } from "react";

import "./card.css";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
    style?: string[];
}

export const Card: FC<CardProps> = ({
    style = [],
    children,
    ...rest
}) => {
    const classes = useMemo(
        () => ["card", ...style].filter(Boolean).join(" "),
        [style]
    );
    return (
        <div className={classes} {...rest}>
            {children}
        </div>
    );
};
