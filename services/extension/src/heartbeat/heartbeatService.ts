import { backendPost } from "../api/client";
import { getConfig } from "../config";

const INTERVAL_MS = 30_000;

export class HeartbeatService {
  private timer: ReturnType<typeof setInterval> | undefined;

  start(): void {
    this.ping(); // immediate first ping
    this.timer = setInterval(() => this.ping(), INTERVAL_MS);
  }

  private ping(): void {
    const config = getConfig();
    backendPost("/api/workspace/heartbeat", {
      project_id: config.projectId,
    }).catch(() => {
      // Silently ignore — workspace may be pausing
    });
  }

  dispose(): void {
    if (this.timer !== undefined) {
      clearInterval(this.timer);
    }
  }
}
