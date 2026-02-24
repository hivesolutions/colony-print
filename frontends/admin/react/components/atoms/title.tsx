import React, { FC, useMemo, HTMLAttributes } from "react";

import "./title.css";

interface TitleProps extends HTMLAttributes<HTMLHeadingElement> {
    level?: 1 | 2 | 3;
    style?: string[];
}

export const Title: FC<TitleProps> = ({
    level = 1,
    style = [],
    children,
    ...rest
}) => {
    const Tag = `h${level}` as keyof JSX.IntrinsicElements;
    const classes = useMemo(
        () =>
            ["title", `title-${level}`, ...style]
                .filter(Boolean)
                .join(" "),
        [level, style]
    );
    return (
        <Tag className={classes} {...rest}>
            {children}
        </Tag>
    );
};
