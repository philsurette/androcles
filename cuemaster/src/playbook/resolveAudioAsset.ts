export function resolveAudioAsset(playbookRootUrl: string, relativePath: string): string {
  return new URL(relativePath, playbookRootUrl.endsWith("/") ? playbookRootUrl : `${playbookRootUrl}/`).toString();
}
