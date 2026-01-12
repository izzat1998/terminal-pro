/**
 * Image utility functions for camera capture and processing
 * Extracted from duplicate implementations across camera pages
 */

/**
 * Convert a base64 data URL to a Blob
 * Used for uploading captured photos to the API
 *
 * @param base64 - Base64 data URL (e.g., "data:image/jpeg;base64,...")
 * @returns Blob object suitable for FormData
 */
export function base64ToBlob(base64: string): Blob {
  const arr = base64.split(',');
  const mime = arr[0].match(/:(.*?);/)?.[1] || 'image/png';
  const bstr = atob(arr[1]);
  let n = bstr.length;
  const u8arr = new Uint8Array(n);
  while (n--) {
    u8arr[n] = bstr.charCodeAt(n);
  }
  return new Blob([u8arr], { type: mime });
}

/**
 * Capture a photo from a video element with automatic resizing
 *
 * @param video - HTML video element with camera stream
 * @param canvas - HTML canvas element for capture
 * @param options - Capture options
 * @returns Base64 data URL of the captured image, or null on failure
 */
export function capturePhotoFromVideo(
  video: HTMLVideoElement,
  canvas: HTMLCanvasElement,
  options: {
    maxWidth?: number;
    maxHeight?: number;
    quality?: number;
    format?: 'image/jpeg' | 'image/png';
  } = {}
): string | null {
  const {
    maxWidth = 1280,
    maxHeight = 720,
    quality = 0.7,
    format = 'image/jpeg',
  } = options;

  const aspectRatio = video.videoWidth / video.videoHeight;

  // Calculate dimensions maintaining aspect ratio
  if (video.videoWidth > maxWidth) {
    canvas.width = maxWidth;
    canvas.height = maxWidth / aspectRatio;
  } else if (video.videoHeight > maxHeight) {
    canvas.height = maxHeight;
    canvas.width = maxHeight * aspectRatio;
  } else {
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
  }

  const context = canvas.getContext('2d');
  if (!context) {
    return null;
  }

  context.drawImage(video, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL(format, quality);
}

/**
 * Create a FormData object with a photo file from base64
 *
 * @param base64 - Base64 data URL of the image
 * @param fieldName - Form field name for the file
 * @param fileName - File name to use
 * @returns FormData with the photo attached
 */
export function createPhotoFormData(
  base64: string,
  fieldName: string = 'image',
  fileName: string = 'photo.jpg'
): FormData {
  const blob = base64ToBlob(base64);
  const formData = new FormData();
  formData.append(fieldName, blob, fileName);
  return formData;
}
