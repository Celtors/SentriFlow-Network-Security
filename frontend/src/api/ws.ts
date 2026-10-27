import type { Event } from "./types";

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
    );
    this.socket = socket;
    socket.onopen = () => socket.send(JSON.stringify({ token: this.token }));
    socket.onmessage = (event) => {
      try {
        this.onEvent(JSON.parse(event.data));
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
