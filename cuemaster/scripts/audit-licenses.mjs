import { existsSync, readdirSync, readFileSync } from "node:fs";
import path from "node:path";

const projectRoot = process.cwd();
const packageRoot = path.join(projectRoot, "node_modules");
const lockfilePath = path.join(projectRoot, "package-lock.json");
const includeDev = process.argv.includes("--include-dev");

const allowedLicenses = new Set([
  "Apache-2.0",
  "BSD-2-Clause",
  "BSD-3-Clause",
  "CC-BY-4.0",
  "ISC",
  "MIT",
  "MIT-0",
  "Zlib"
]);

const prohibitedPatterns = [
  /\bAGPL\b/i,
  /\bBUSL\b/i,
  /\bCommons Clause\b/i,
  /\bLGPL\b/i,
  /\bSSPL\b/i
];

const licenseOverrides = new Map([
  ["jszip", "MIT"],
  ["pako", "MIT AND Zlib"]
]);

class PackageLicense {
  constructor(packageJsonPath, lockPackage = null) {
    const packageJson = JSON.parse(readFileSync(packageJsonPath, "utf8"));
    this.name = packageJson.name;
    this.version = packageJson.version ?? lockPackage?.version;
    this.license = licenseOverrides.get(this.name) ?? lockPackage?.license ?? packageJson.license ?? "MISSING";
    this.packageDir = path.dirname(packageJsonPath);
  }

  isAllowed() {
    if (this.license === "MISSING") {
      return false;
    }

    if (prohibitedPatterns.some((pattern) => pattern.test(this.license))) {
      return false;
    }

    const tokens = this.license
      .replace(/[()]/g, "")
      .split(/\s+(?:AND|OR)\s+/i)
      .map((token) => token.trim());

    return tokens.every((token) => allowedLicenses.has(token));
  }

  hasLicenseFile() {
    return readdirSync(this.packageDir).some((entry) => /^licen[cs]e|copying|notice/i.test(entry));
  }
}

class LicenseAuditor {
  constructor(root) {
    this.root = root;
    this.lockPackages = this.readLockPackages();
  }

  audit() {
    if (!existsSync(this.root)) {
      throw new Error("node_modules is missing. Run npm install before auditing licenses.");
    }

    const packages = this.collectPackages().sort((a, b) => a.name.localeCompare(b.name));
    const failures = packages.filter((pkg) => !pkg.isAllowed());
    const missingLicenseFiles = packages.filter((pkg) => !pkg.hasLicenseFile());

    for (const pkg of packages) {
      const licenseFile = pkg.hasLicenseFile() ? "license-file" : "missing-license-file";
      console.log(`${pkg.name}@${pkg.version}: ${pkg.license} (${licenseFile})`);
    }

    if (failures.length > 0) {
      const summary = failures.map((pkg) => `${pkg.name}@${pkg.version}: ${pkg.license}`).join("\n");
      throw new Error(`License audit failed:\n${summary}`);
    }

    if (missingLicenseFiles.length > 0) {
      const summary = missingLicenseFiles.map((pkg) => `${pkg.name}@${pkg.version}`).join(", ");
      console.warn(`License file review warning: ${summary}`);
    }

    console.log(`License audit passed for ${packages.length} installed packages.`);
  }

  collectPackages() {
    const packages = [];

    for (const [packagePath, lockPackage] of this.lockPackages) {
      if (packagePath === "" || (!includeDev && lockPackage.dev)) {
        continue;
      }

      const packageJsonPath = path.join(projectRoot, packagePath, "package.json");
      if (!existsSync(packageJsonPath)) {
        if (lockPackage.optional) {
          continue;
        }
        throw new Error(`Installed package metadata missing for ${packagePath}. Run npm install.`);
      }

      packages.push(new PackageLicense(packageJsonPath, lockPackage));
    }

    return packages;
  }

  readLockPackages() {
    if (!existsSync(lockfilePath)) {
      throw new Error("package-lock.json is missing. Run npm install before auditing licenses.");
    }

    const lockfile = JSON.parse(readFileSync(lockfilePath, "utf8"));
    return Object.entries(lockfile.packages ?? {});
  }
}

new LicenseAuditor(packageRoot).audit();
