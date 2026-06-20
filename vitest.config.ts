import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: [
      "ports/tests/**/*.test.ts",
      "examples/**/test.ts",
      "examples/**/*.test.ts",
      "examples/**/*.spec.ts",
    ],
    environment: "node",
    testTimeout: 10_000,
  },
});
