export type FileHandle = {
  path: string;
  blob: Blob;
};

export async function readBrowserFile(file: File): Promise<FileHandle> {
  return { path: file.name, blob: file };
}
