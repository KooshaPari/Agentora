import { DynamicStructuredTool } from "@langchain/core/tools";
import { z } from "zod";

export interface McpToolMetadata {
  name: string;
  description: string;
  schema: {
    properties?: Record<string, { type?: string; description?: string }>;
    required?: string[];
  };
}

export function mcpToLangChainTool(
  fn: Function & { __mcp_metadata__?: McpToolMetadata }
): DynamicStructuredTool {
  if (!fn.__mcp_metadata__) {
    throw new Error("Function must be decorated with MCP metadata");
  }

  const metadata = fn.__mcp_metadata__;
  const shape: Record<string, z.ZodTypeAny> = {};

  for (const [name, prop] of Object.entries(metadata.schema.properties || {})) {
    let schemaType: z.ZodTypeAny;
    switch (prop.type) {
      case "string":
        schemaType = z.string();
        break;
      case "integer":
        schemaType = z.number().int();
        break;
      case "number":
        schemaType = z.number();
        break;
      case "boolean":
        schemaType = z.boolean();
        break;
      case "array":
        schemaType = z.array(z.any());
        break;
      case "object":
        schemaType = z.record(z.any());
        break;
      default:
        schemaType = z.any();
    }
    if (prop.description) {
      schemaType = schemaType.describe(prop.description);
    }
    if (!metadata.schema.required?.includes(name)) {
      schemaType = schemaType.optional();
    }
    shape[name] = schemaType;
  }

  return new DynamicStructuredTool({
    name: metadata.name,
    description: metadata.description,
    schema: z.object(shape),
    func: async (input: Record<string, any>) => fn(input),
  });
}
