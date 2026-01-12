/**
 * Reusable Camera Overlay Component
 * Full-screen camera view with capture and cancel controls
 */

import type { FC, RefObject } from 'react';
import { Button } from 'antd-mobile';
import { X, Circle } from 'lucide-react';

interface CameraOverlayProps {
  /** Ref to the video element */
  videoRef: RefObject<HTMLVideoElement>;
  /** Ref to the canvas element (used for capturing) */
  canvasRef: RefObject<HTMLCanvasElement>;
  /** Whether camera is loading */
  isLoading?: boolean;
  /** Loading text */
  loadingText?: string;
  /** Loading subtext */
  loadingSubtext?: string;
  /** Called when cancel button is clicked */
  onCancel: () => void;
  /** Called when capture button is clicked */
  onCapture: () => void;
  /** Whether capture button is disabled */
  captureDisabled?: boolean;
}

/**
 * Full-screen camera overlay with video preview and control buttons
 *
 * @example
 * ```tsx
 * <CameraOverlay
 *   videoRef={videoRef}
 *   canvasRef={canvasRef}
 *   isLoading={isCameraLoading}
 *   onCancel={() => setIsCameraOpen(false)}
 *   onCapture={handleCapture}
 * />
 * ```
 */
export const CameraOverlay: FC<CameraOverlayProps> = ({
  videoRef,
  canvasRef,
  isLoading = false,
  loadingText = 'Камера юкланмоқда...',
  loadingSubtext = 'Илтимос кутинг',
  onCancel,
  onCapture,
  captureDisabled = false,
}) => {
  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'black',
        zIndex: 9999,
        display: 'flex',
        flexDirection: 'column',
      }}
    >
      {/* Camera view - full height */}
      <div
        style={{
          flex: 1,
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <video
          ref={videoRef}
          autoPlay
          playsInline
          muted
          style={{
            width: '100%',
            height: '100%',
            objectFit: 'cover',
          }}
          onLoadedMetadata={(e) => {
            const video = e.target as HTMLVideoElement;
            video.play().catch(err => console.error('Error playing video on metadata:', err));
          }}
        />

        {/* Loading indicator */}
        {isLoading && (
          <div
            style={{
              position: 'absolute',
              top: '50%',
              left: '50%',
              transform: 'translate(-50%, -50%)',
              textAlign: 'center',
              color: 'white',
            }}
          >
            <div
              style={{
                fontSize: '16px',
                marginBottom: '12px',
              }}
            >
              {loadingText}
            </div>
            <div
              style={{
                fontSize: '14px',
                opacity: 0.7,
              }}
            >
              {loadingSubtext}
            </div>
          </div>
        )}

        {/* Camera controls overlay */}
        <div
          style={{
            position: 'absolute',
            bottom: '40px',
            left: 0,
            right: 0,
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            gap: '40px',
          }}
        >
          <Button
            shape='rounded'
            color='danger'
            size='large'
            onClick={onCancel}
            style={{
              width: '60px',
              height: '60px',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
            }}
          >
            <X size={30} />
          </Button>

          <Button
            shape='rounded'
            color='primary'
            size='large'
            onClick={onCapture}
            disabled={captureDisabled}
            style={{
              width: '80px',
              height: '80px',
              display: 'flex',
              justifyContent: 'center',
              alignItems: 'center',
              opacity: captureDisabled ? 0.5 : 1,
            }}
          >
            <Circle size={60} />
          </Button>
        </div>
      </div>

      <canvas ref={canvasRef} style={{ display: 'none' }} />
    </div>
  );
};
