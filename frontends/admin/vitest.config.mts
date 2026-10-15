import { defineConfig } from "vitest/config";

export default defineConfig({
    test: {
        environment: "jsdom",
        include: ["react/test/**/*.{ts,tsx}"],
        coverage: {
            provider: "v8",
            include: ["react/**/*.{ts,tsx}"],
            exclude: ["react/test/**"],
            reporter: ["text"]
        }
    }
});
