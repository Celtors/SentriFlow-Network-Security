import type { Event } from "./types";
import { api } from "./client";
import type { Snapshot } from "./types";

export class LiveClient {
  private token: string;
  private onEvent: (event: Event) => void;
  private onStatus: (status: string) => void;
  private socket: WebSocket | null = null;
  private timer: ReturnType<typeof setTimeout> | undefined;
  private stopped = false;
  constructor(
    token: string,
    onEvent: (event: Event) => void,
    onStatus: (status: string) => void,
  ) {
    this.token = token;
    this.onEvent = onEvent;
    this.onStatus = onStatus;
  }
  connect() {
    this.onStatus("Connecting");
    const socket = new WebSocket(
      `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`,
      ["sentriflow", this.token],
    );
    this.socket = socket;
    socket.onopen = async () => {
      try {
        const snapshot = await api<Snapshot>("/snapshot");
        if (
          !this.stopped &&
          this.socket === socket &&
          socket.readyState === WebSocket.OPEN
        ) {
          this.onEvent({
            type: "snapshot",
            ts: new Date().toISOString(),
            data: snapshot,
          });
          this.onStatus("Live");
        }
      } catch {
        if (!this.stopped) this.onStatus("Local service unavailable");
      }
    };
    socket.onmessage = (event) => {
      try {
        const message: Event = JSON.parse(event.data);
        if (message.type === "halt.requested") {
          const halt = message.data as {
            flow: Record<string, unknown>;
            deadline: string;
          };
          message.data = {
            ...halt.flow,
            state: "held",
            deadline: halt.deadline,
          };
        }
        this.onEvent(message);
        this.onStatus("Live");
      } catch {
        this.onStatus("Invalid live event");
      }
    };
    socket.onclose = (event) => {
      if (this.stopped) return;
      this.onStatus(
        event.code === 1008
          ? "Token rejected; reconnect with current token"
          : "Disconnected",
      );
      if (event.code !== 1008)
        this.timer = setTimeout(() => this.connect(), 2000);
    };
    socket.onerror = () => this.onStatus("Local service unavailable");
  }
  close() {
    this.stopped = true;
    clearTimeout(this.timer);
    this.socket?.close();
  }
}
