export type PackageFormatCompatibility = "supported" | "newer_minor";

export function validatePackageFormatVersion(
  manifest: unknown,
  packageType: string,
  supportedVersion: string
): PackageFormatCompatibility {
  if (!isObject(manifest)) {
    throw new Error("Manifest must be an object");
  }
  if (manifest.package_type !== packageType) {
    throw new Error(`Expected ${packageType} package`);
  }
  if (typeof manifest.format_version !== "string") {
    throw new Error(`${packageType} package is missing format_version`);
  }
  const packageVersion = parseFormatVersion(manifest.format_version);
  const supported = parseFormatVersion(supportedVersion);
  if (packageVersion.major !== supported.major) {
    throw new Error(
      `Unsupported ${packageType} format version ${manifest.format_version}; supported version is ${supportedVersion}`
    );
  }
  if (packageVersion.minor > supported.minor) {
    console.warn(
      `${packageType} format version ${manifest.format_version} is newer than supported ${supportedVersion}; newer fields may be ignored.`
    );
    return "newer_minor";
  }
  return "supported";
}

function parseFormatVersion(value: string): { major: number; minor: number; patch: number } {
  const match = /^(\d+)\.(\d+)\.(\d+)$/.exec(value);
  if (!match) {
    throw new Error(`Invalid format_version: ${value}`);
  }
  return {
    major: Number(match[1]),
    minor: Number(match[2]),
    patch: Number(match[3])
  };
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

