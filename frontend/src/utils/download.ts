/**
 * Utility functions for file downloads
 */

/**
 * Downloads a Blob as a file
 * @param blob - The Blob to download
 * @param filename - The name for the downloaded file
 */
export function downloadBlob(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  window.URL.revokeObjectURL(url);
}

/**
 * Downloads data from a Response as a file
 * @param response - Fetch Response object
 * @param filename - The name for the downloaded file
 */
export async function downloadResponse(response: Response, filename: string): Promise<void> {
  const blob = await response.blob();
  downloadBlob(blob, filename);
}
