#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

const server = new McpServer({
  name: "location-tracker-mcp",
  version: "0.1.0"
});

server.registerTool(
  "get-current-location",
  {
    description: "Возвращает примерное текущее местоположение по публичному IP (город, страна, координаты).",
    inputSchema: {}
  },
  async () => {
    // Using ip-api.com - free, no rate limits for non-commercial use
    const response = await fetch("http://ip-api.com/json/?fields=status,message,country,regionName,city,lat,lon,isp,query");

    if (!response.ok) {
      throw new Error(`Failed to fetch location: ${response.status} ${response.statusText}`);
    }

    const data = await response.json();

    if (data.status === "fail") {
      throw new Error(`Geolocation failed: ${data.message}`);
    }

    const result = {
      ip: data.query,
      city: data.city,
      region: data.regionName,
      country: data.country,
      latitude: data.lat,
      longitude: data.lon,
      isp: data.isp
    };

    return {
      content: [
        {
          type: "text",
          text: JSON.stringify(result, null, 2)
        }
      ]
    };
  }
);

async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch(error => {
  console.error("Server error:", error);
  process.exit(1);
});
