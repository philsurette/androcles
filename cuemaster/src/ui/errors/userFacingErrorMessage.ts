import { MicrophonePermissionError } from "../../platform/microphone";
import { PlaybookImportError } from "../../playbook/playbookImportError";

export function userFacingErrorMessage(error: unknown): string {
  if (error instanceof PlaybookImportError) {
    return error.message;
  }
  if (error instanceof MicrophonePermissionError) {
    return error.message;
  }
  if (isStorageQuotaError(error)) {
    return "Local storage is full. Remove an imported Playbook or free browser storage, then try again.";
  }
  if (isIndexedDbError(error)) {
    return "Local browser storage could not be read. Try refreshing; if the problem persists, clear Cuemaster site data and re-import Playbooks.";
  }
  if (error instanceof Error && error.message.includes("Audio asset not found")) {
    return error.message;
  }
  if (isAutoplayError(error)) {
    return "The browser blocked playback. Press a playback button again to start audio.";
  }
  if (error instanceof Error && error.message.includes("Audio playback failed")) {
    return "Audio playback failed. This browser may not support the Playbook audio format.";
  }
  if (error instanceof Error) {
    return error.message;
  }
  return "Something went wrong.";
}

function isStorageQuotaError(error: unknown): boolean {
  const name = errorName(error);
  return name === "QuotaExceededError" || name === "NS_ERROR_DOM_QUOTA_REACHED";
}

function isAutoplayError(error: unknown): boolean {
  return errorName(error) === "NotAllowedError";
}

function isIndexedDbError(error: unknown): boolean {
  return ["DataError", "InvalidStateError", "ReadOnlyError", "TransactionInactiveError", "UnknownError", "VersionError"].includes(
    errorName(error) ?? ""
  );
}

function errorName(error: unknown): string | undefined {
  if (error instanceof DOMException || error instanceof Error) {
    return error.name;
  }
  return undefined;
}
