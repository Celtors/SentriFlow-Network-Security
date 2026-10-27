import { create } from "zustand";
import type { Flow, Rate, Snapshot, SpeedTick } from "../api/types";

interface TrafficState {
  snapshot: Snapshot | null;
  status: string;
  error: string;
  rates: Rate[];
  setSnapshot: (snapshot: Snapshot) => void;
  setStatus: (status: string) => void;
  setError: (error: string) => void;
  upsert: (flow: Flow) => void;
  speed: (tick: SpeedTick, ts: string) => void;
  reset: () => void;
}
export const useTrafficStore = create<TrafficState>((set) => ({
  snapshot: null,
  status: "Disconnected",
  error: "",
  rates: [],
  setSnapshot: (snapshot) => set({ snapshot }),
  setStatus: (status) => set({ status }),
  setError: (error) => set({ error }),
  upsert: (flow) =>
    set((state) => ({
      snapshot: state.snapshot
        ? {
            ...state.snapshot,
            flows: [
              flow,
              ...state.snapshot.flows.filter((f) => f.id !== flow.id),
            ]
              .sort((a, b) => b.ts.localeCompare(a.ts))
              .slice(0, 200),
          }
        : null,
    })),
  speed: (tick, ts) =>
    set((state) => ({
      rates: [
        ...state.rates.slice(-29),
        {
          time: new Date(ts).toLocaleTimeString(),
          upload: tick.upload_bps,
          download: tick.download_bps,
        },
      ],
      snapshot: state.snapshot
        ? { ...state.snapshot, processes: tick.processes }
        : null,
    })),
  reset: () =>
    set({ snapshot: null, status: "Disconnected", error: "", rates: [] }),
}));
