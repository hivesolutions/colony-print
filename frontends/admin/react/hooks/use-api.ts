import { useContext } from "react";

import { APIContext } from "../contexts";
import { ColonyPrintAPI } from "../api/colony-print";

export const useAPI = (): ColonyPrintAPI => {
    return useContext(APIContext);
};
