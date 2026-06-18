import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["ports/tests/**/*.test.ts"],
    environment: "node",
    testTimeout: 10_000,
  },
});
