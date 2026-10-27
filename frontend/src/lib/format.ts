export const bytes = (value: number) =>
  value < 1000
    ? `${value.toFixed(0)} B`
    : value < 1e6
      ? `${(value / 1000).toFixed(1)} KB`
      : `${(value / 1e6).toFixed(1)} MB`;
export const time = (value: string) => new Date(value).toLocaleTimeString();
export const patternLabel = (value: string) => value.replaceAll("_", " ");
