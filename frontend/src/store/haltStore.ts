import { create } from "zustand";
import type { Flow } from "../api/types";

export const useHaltStore = create<{
  pending: Flow[];
  replace: (items: Flow[]) => void;
  add: (flow: Flow) => void;
  remove: (id: string) => void;
}>((set) => ({
  pending: [],
  replace: (pending) => set({ pending }),
  add: (flow) =>
    set((state) => ({
      pending: [...state.pending.filter((f) => f.id !== flow.id), flow],
    })),
  remove: (id) =>
    set((state) => ({ pending: state.pending.filter((f) => f.id !== id) })),
}));
