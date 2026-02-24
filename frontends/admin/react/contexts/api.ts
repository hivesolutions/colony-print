import { createContext } from "react";

import { ColonyPrintAPI } from "../api/colony-print";

export const APIContext = createContext<ColonyPrintAPI>(
    new ColonyPrintAPI()
);
