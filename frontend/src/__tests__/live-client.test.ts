// @vitest-environment jsdom
import { afterEach, expect, it, vi } from "vitest";
import { LiveClient } from "../api/ws";

class Socket {
  static instances: Socket[] = [];
  url: string;
  protocols: string[];
  onmessage: ((event: { data: string }) => void) | null = null;
  onclose: ((event: { code: number }) => void) | null = null;
  onerror: (() => void) | null = null;
  constructor(url: string, protocols: string[]) {
    this.url = url;
    this.protocols = protocols;
    Socket.instances.push(this);
  }
  close() {
    this.onclose?.({ code: 1000 });
  }
  emit(event: object) {
    this.onmessage?.({ data: JSON.stringify(event) });
  }
}

function start() {
  vi.stubGlobal("WebSocket", Socket);
  const onEvent = vi.fn(),
    onStatus = vi.fn();
  const client = new LiveClient("session-token", onEvent, onStatus);
  client.connect();
  return { client, onEvent, onStatus, socket: Socket.instances.at(-1)! };
}

afterEach(() => {
  vi.unstubAllGlobals();
  vi.useRealTimers();
  Socket.instances = [];
});

it("authenticates at handshake and applies the server snapshot before queued holds", () => {
  const { client, onEvent, socket } = start();
  expect(socket.protocols).toEqual(["sentriflow", "session-token"]);
  expect(socket.url).toMatch(/\/ws$/);
  const snapshot = { flows: [], pending: [] };
  socket.emit({ type: "system.status", ts: "now", data: { snapshot } });
  socket.emit({
    type: "halt.requested",
    ts: "later",
    data: {
      id: "held",
      flow: { id: "held", host: "example.test" },
      deadline: "deadline",
    },
  });
  expect(onEvent.mock.calls[0][0]).toEqual({
    type: "snapshot",
    ts: "now",
    data: snapshot,
  });
  expect(onEvent.mock.calls.at(-1)![0].data).toEqual({
    id: "held",
    host: "example.test",
    state: "held",
    deadline: "deadline",
  });
  client.close();
});

it("ignores late events and reconnect callbacks after disconnecting the session", () => {
  vi.useFakeTimers();
  const { client, onEvent, onStatus, socket } = start();
  socket.onclose?.({ code: 1006 });
  client.close();
  const statuses = onStatus.mock.calls.length;
  socket.emit({ type: "flow.completed", ts: "late", data: {} });
  socket.onerror?.();
  vi.advanceTimersByTime(5000);
  client.connect();
  expect(onEvent).not.toHaveBeenCalled();
  expect(onStatus).toHaveBeenCalledTimes(statuses);
  expect(Socket.instances).toHaveLength(1);
});

it("ignores an old socket after a new connection is established", () => {
  const { client, onEvent, socket } = start();
  client.connect();
  socket.emit({ type: "flow.completed", ts: "stale", data: {} });
  expect(onEvent).not.toHaveBeenCalled();
  client.close();
});
