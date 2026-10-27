import { useHaltStore } from "../store/haltStore";

export function useHaltQueue() {
  return useHaltStore((state) => state.pending);
}
