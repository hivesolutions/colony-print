import { createContext } from "react";

export interface DataContextType {
    username: string | null;
    setUsername: (username: string | null) => void;
}

export const DataContext = createContext<DataContextType>({
    username: null,
    setUsername: () => {}
});
