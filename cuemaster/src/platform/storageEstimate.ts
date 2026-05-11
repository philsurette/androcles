export type StorageEstimate = {
  usageBytes: number | null;
  quotaBytes: number | null;
  persisted: boolean | null;
};

export async function estimateStorage(): Promise<StorageEstimate> {
  const estimate = await navigator.storage?.estimate?.();
  return {
    usageBytes: estimate?.usage ?? null,
    quotaBytes: estimate?.quota ?? null,
    persisted: (await navigator.storage?.persisted?.()) ?? null
  };
}

export async function requestPersistentStorage(): Promise<boolean | null> {
  return (await navigator.storage?.persist?.()) ?? null;
}

export function formatBytes(bytes: number | null): string {
  if (bytes === null) {
    return "unknown";
  }
  if (bytes < 1024) {
    return `${bytes} B`;
  }
  const units = ["KB", "MB", "GB", "TB"];
  let value = bytes / 1024;
  for (const unit of units) {
    if (value < 1024 || unit === units[units.length - 1]) {
      return `${value.toFixed(value >= 10 ? 0 : 1)} ${unit}`;
    }
    value /= 1024;
  }
  return `${bytes} B`;
}
