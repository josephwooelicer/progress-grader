/**
 * Runtime config — reads env vars injected by the workspace container.
 * All values are set by the backend when it provisions the container.
 */
export interface Config {
  proxyUrl: string;
  backendUrl: string;
  projectId: string;
  workspaceId: string;
  /** Short-lived JWT for this student+workspace, written to the workspace volume at startup. */
  platformToken: string;
}

function required(name: string): string {
  const val = process.env[name];
  if (!val) {
    throw new Error(`Progress Grader: missing required env var ${name}. Is this a managed workspace?`);
  }
  return val;
}

let _config: Config | null = null;

export function getConfig(): Config {
  if (_config) return _config;
  _config = {
    proxyUrl: process.env["PROXY_URL"] ?? "http://proxy:8001",
    backendUrl: process.env["BACKEND_URL"] ?? "http://backend:8000",
    projectId: required("PROJECT_ID"),
    workspaceId: required("WORKSPACE_ID"),
    platformToken: required("PLATFORM_TOKEN"),
  };
  return _config;
}
