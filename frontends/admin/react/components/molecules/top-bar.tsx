import React, { FC, useContext } from "react";

import { DataContext } from "../../contexts";

import "./top-bar.css";

export const TopBar: FC = () => {
    const { username } = useContext(DataContext);
    return (
        <header className="top-bar">
            <div className="top-bar-brand">Colony Print</div>
            {username && (
                <div className="top-bar-user">{username}</div>
            )}
        </header>
    );
};
