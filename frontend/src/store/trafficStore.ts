import { create } from "zustand";
import type { Flow, Rate, Snapshot, SpeedTick, Website } from "../api/types";

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
  website: (website: Website, currentId: string | null) => void;
}
export const useTrafficStore = create<TrafficState>((set) => ({
  snapshot: null,
  status: "Disconnected",
  error: "",
  rates: [],
  setSnapshot: (snapshot) => set({ snapshot }),
  setStatus: (status) => set({ status }),
  setError: (error) => set({ error }),
  website: (website, currentId) =>
    set((state) => {
      if (!state.snapshot) return {};
      const websites = [
        website,
        ...(state.snapshot.websites ?? []).filter((s) => s.id !== website.id),
      ];
      while (websites.length > 50) {
        let index = websites.length - 1;
        if (websites[index].id === currentId) index -= 1;
        websites.splice(index, 1);
      }
      return {
        snapshot: {
          ...state.snapshot,
          current_website_id: currentId,
          websites,
        },
      };
    }),
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
