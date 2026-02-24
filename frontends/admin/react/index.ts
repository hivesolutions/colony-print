import React from "react";
import ReactDOM from "react-dom/client";

import { App } from "./app";

export const startApp = () => {
    const element = document.getElementById("app");
    if (!element) return;
    const root = ReactDOM.createRoot(element);
    root.render(React.createElement(App));
};
