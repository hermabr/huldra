import { defineConfig } from "orval";

export default defineConfig({
  api: {
    input: "../openapi.json",
    output: {
      mode: "tags-split",
      target: "src/api/endpoints",
      schemas: "src/api/models",
      client: "react-query",
      override: {
        mutator: {
          path: "./src/lib/api-client.ts",
          name: "customInstance",
        },
        query: {
          useQuery: true,
          useMutation: true,
        },
      },
    },
  },
  apiZod: {
    input: "../openapi.json",
    output: {
      mode: "single",
      client: "zod",
      target: "src/api/zod/schemas.ts",
    },
  },
});


