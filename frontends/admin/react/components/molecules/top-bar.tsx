import React, { FC, useContext } from "react";

import { DataContext } from "../../contexts";

import "./top-bar.css";

interface TopBarProps {
    onToggleSidebar?: () => void;
}

export const TopBar: FC<TopBarProps> = ({ onToggleSidebar }) => {
    const { username } = useContext(DataContext);
    return (
        <header className="top-bar">
            <div className="top-bar-left">
                {onToggleSidebar && (
                    <button
                        className="top-bar-toggle"
                        onClick={onToggleSidebar}
                        aria-label="Toggle menu"
                    >
                        <svg
                            width="20"
                            height="20"
                            viewBox="0 0 20 20"
                            fill="none"
                            stroke="currentColor"
                            strokeWidth="2"
                            strokeLinecap="round"
                        >
                            <line x1="3" y1="5" x2="17" y2="5" />
                            <line x1="3" y1="10" x2="17" y2="10" />
                            <line x1="3" y1="15" x2="17" y2="15" />
                        </svg>
                    </button>
                )}
                <div className="top-bar-brand">Colony Print</div>
            </div>
            {username && (
                <div className="top-bar-user">{username}</div>
            )}
        </header>
    );
};
