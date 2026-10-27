import { useEffect } from "react";
import { api } from "../api/client";
import { LiveClient } from "../api/ws";
import type { Flow, Snapshot, SpeedTick } from "../api/types";
import { useTrafficStore } from "../store/trafficStore";
import { useHaltStore } from "../store/haltStore";

export function useLiveTraffic(token: string) {
  useEffect(() => {
    if (!token) return;
    let stopped = false;
    let refresh: ReturnType<typeof setTimeout> | undefined;
    const accept = (snapshot: Snapshot) => {
      useTrafficStore.getState().setSnapshot(snapshot);
      useHaltStore.getState().replace(snapshot.pending);
    };
    const client = new LiveClient(
      token,
      (event) => {
        if (event.type === "snapshot") accept(event.data as Snapshot);
        else if (event.type === "speed.tick")
          useTrafficStore.getState().speed(event.data as SpeedTick, event.ts);
        else {
          if (
            event.type === "flow.started" ||
            event.type === "flow.completed" ||
            event.type === "halt.requested"
          ) {
            const flow = event.data as Flow;
            useTrafficStore.getState().upsert(flow);
            if (flow.state === "held") useHaltStore.getState().add(flow);
            else useHaltStore.getState().remove(flow.id);
            if (
              flow.state === "held" &&
              document.hidden &&
              typeof Notification !== "undefined" &&
              Notification.permission === "granted"
            ) {
              const notice = new Notification("SentriFlow paused a transfer", {
                body: `${flow.process_name} to ${flow.host}. Open dashboard to decide.`,
              });
              notice.onclick = () => {
                window.focus();
                notice.close();
              };
            }
          }
          if (event.type === "halt.resolved")
            useHaltStore.getState().remove((event.data as { id: string }).id);
          if (!refresh)
            refresh = setTimeout(async () => {
              refresh = undefined;
              try {
                const data = await api<Snapshot>("/snapshot");
                if (!stopped) accept(data);
              } catch (error) {
                if (!stopped)
                  useTrafficStore.getState().setError((error as Error).message);
              }
            }, 200);
        }
      },
      (status) => useTrafficStore.getState().setStatus(status),
    );
    client.connect();
    return () => {
      stopped = true;
      clearTimeout(refresh);
      client.close();
    };
  }, [token]);
}
