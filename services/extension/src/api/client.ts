import * as https from "https";
import * as http from "http";
import { URL } from "url";
import { getConfig } from "../config";

export interface ChatMessage {
  role: "user" | "assistant" | "system";
  content: string;
}

export interface StreamChunk {
  delta?: string;
  done?: boolean;
  context_usage_pct?: number;
  input_tokens?: number;
  output_tokens?: number;
  error?: string;
}

/**
 * Stream a chat request to the proxy.
 * Calls onChunk for each SSE data event, returns when stream ends.
 */
export async function streamChat(
  conversationId: string,
  messages: ChatMessage[],
  systemPrompt: string | undefined,
  onChunk: (chunk: StreamChunk) => void,
  signal?: AbortSignal
): Promise<void> {
  const config = getConfig();
  const url = new URL("/v1/chat", config.proxyUrl);

  const body = JSON.stringify({
    conversation_id: conversationId,
    project_id: config.projectId,
    messages,
    system_prompt: systemPrompt ?? null,
  });

  return new Promise((resolve, reject) => {
    const lib = url.protocol === "https:" ? https : http;
    const req = lib.request(
      {
        hostname: url.hostname,
        port: url.port || (url.protocol === "https:" ? 443 : 80),
        path: url.pathname,
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Content-Length": Buffer.byteLength(body),
          Authorization: `Bearer ${config.platformToken}`,
        },
      },
      (res) => {
        if (res.statusCode === 429) {
          // Context limit reached
          let raw = "";
          res.on("data", (d: Buffer) => (raw += d.toString()));
          res.on("end", () => {
            try {
              const detail = JSON.parse(raw)?.detail;
              onChunk({ error: detail?.message ?? "Context limit reached. Start a new conversation." });
            } catch {
              onChunk({ error: "Context limit reached. Start a new conversation." });
            }
            resolve();
          });
          return;
        }

        if (res.statusCode === 403) {
          onChunk({ error: "consent_required" });
          resolve();
          return;
        }

        if (!res.statusCode || res.statusCode >= 400) {
          reject(new Error(`Proxy returned ${res.statusCode}`));
          return;
        }

        let buffer = "";
        res.on("data", (data: Buffer) => {
          buffer += data.toString();
          const lines = buffer.split("\n");
          buffer = lines.pop() ?? "";

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue;
            const payload = line.slice(6).trim();
            if (payload === "[DONE]") continue;
            try {
              onChunk(JSON.parse(payload) as StreamChunk);
            } catch {
              // skip malformed
            }
          }
        });

        res.on("end", () => resolve());
        res.on("error", reject);
      }
    );

    req.on("error", reject);

    if (signal) {
      signal.addEventListener("abort", () => {
        req.destroy();
        resolve();
      });
    }

    req.write(body);
    req.end();
  });
}

/** POST to the backend API. Returns parsed JSON. */
export async function backendPost<T>(path: string, body: unknown): Promise<T> {
  const config = getConfig();
  const url = new URL(path, config.backendUrl);

  const bodyStr = JSON.stringify(body);
  return new Promise((resolve, reject) => {
    const lib = url.protocol === "https:" ? https : http;
    const req = lib.request(
      {
        hostname: url.hostname,
        port: url.port || (url.protocol === "https:" ? 443 : 80),
        path: url.pathname,
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Content-Length": Buffer.byteLength(bodyStr),
          Authorization: `Bearer ${config.platformToken}`,
        },
      },
      (res) => {
        let raw = "";
        res.on("data", (d: Buffer) => (raw += d.toString()));
        res.on("end", () => {
          try {
            resolve(JSON.parse(raw) as T);
          } catch {
            resolve(raw as unknown as T);
          }
        });
        res.on("error", reject);
      }
    );
    req.on("error", reject);
    req.write(bodyStr);
    req.end();
  });
}

/** GET from the backend API. Returns parsed JSON. */
export async function backendGet<T>(path: string): Promise<T> {
  const config = getConfig();
  const url = new URL(path, config.backendUrl);

  return new Promise((resolve, reject) => {
    const lib = url.protocol === "https:" ? https : http;
    const req = lib.request(
      {
        hostname: url.hostname,
        port: url.port || (url.protocol === "https:" ? 443 : 80),
        path: url.pathname,
        method: "GET",
        headers: {
          Authorization: `Bearer ${config.platformToken}`,
        },
      },
      (res) => {
        let raw = "";
        res.on("data", (d: Buffer) => (raw += d.toString()));
        res.on("end", () => {
          try {
            resolve(JSON.parse(raw) as T);
          } catch {
            resolve(raw as unknown as T);
          }
        });
        res.on("error", reject);
      }
    );
    req.on("error", reject);
    req.end();
  });
}
