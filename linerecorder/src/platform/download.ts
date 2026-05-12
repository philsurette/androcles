export type DownloadFile = {
  blob: Blob;
  fileName: string;
};

export interface DownloadService {
  download(file: DownloadFile): void;
}

export class BrowserDownloadService implements DownloadService {
  download(file: DownloadFile): void {
    const url = URL.createObjectURL(file.blob);
    try {
      const link = document.createElement("a");
      link.href = url;
      link.download = file.fileName;
      link.style.display = "none";
      document.body.append(link);
      link.click();
      link.remove();
    } finally {
      URL.revokeObjectURL(url);
    }
  }
}

export const browserDownloadService = new BrowserDownloadService();
