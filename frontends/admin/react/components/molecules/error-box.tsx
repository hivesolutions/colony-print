import React, { FC, useMemo } from "react";

import "./error-box.css";

interface ErrorBoxProps {
    message: string;
    style?: string[];
}

export const ErrorBox: FC<ErrorBoxProps> = ({
    message,
    style = []
}) => {
    const classes = useMemo(
        () => ["error-box", ...style].filter(Boolean).join(" "),
        [style]
    );
    return <div className={classes}>{message}</div>;
};
