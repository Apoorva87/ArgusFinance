import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { loadEnv } from "vite";

const defaultApiPort = "8765";

export default defineConfig(({ mode }) => {
  const configuredApiPort = loadEnv(mode, ".", "ARGUS_DASHBOARD_").ARGUS_DASHBOARD_API_PORT;
  const apiPort =
    configuredApiPort !== undefined &&
    /^[1-9]\d{0,4}$/.test(configuredApiPort) &&
    Number(configuredApiPort) <= 65535
      ? configuredApiPort
      : defaultApiPort;

  return {
    plugins: [react()],
    server: {
      proxy: {
        "/api": {
          target: `http://127.0.0.1:${apiPort}`,
        },
      },
    },
    test: {
      environment: "jsdom",
      globals: true,
      css: true,
    },
  };
});
