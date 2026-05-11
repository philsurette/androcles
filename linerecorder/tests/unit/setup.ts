import "@testing-library/jest-dom/vitest";
import "fake-indexeddb/auto";

Object.defineProperty(window, "isSecureContext", {
  configurable: true,
  value: true
});
