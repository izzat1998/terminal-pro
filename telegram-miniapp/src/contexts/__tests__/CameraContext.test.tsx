import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import type { ReactNode } from 'react';
import { CameraProvider, useCamera } from '../CameraContext';

describe('CameraContext', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('Provider setup', () => {
    it('should throw error when useCamera is used outside CameraProvider', () => {
      // Suppress console.error for this test
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      expect(() => {
        renderHook(() => useCamera());
      }).toThrow('useCamera must be used within a CameraProvider');

      consoleSpy.mockRestore();
    });

    it('should provide context when used within CameraProvider', () => {
      const wrapper = ({ children }: { children: ReactNode }) => (
        <CameraProvider>{children}</CameraProvider>
      );

      const { result } = renderHook(() => useCamera(), { wrapper });

      expect(result.current).toBeDefined();
      expect(result.current.streamRef).toBeDefined();
      expect(typeof result.current.requestCameraAccess).toBe('function');
      expect(typeof result.current.stopCamera).toBe('function');
      expect(typeof result.current.isCameraActive).toBe('boolean');
    });
  });

  describe('Camera stream management', () => {
    it('should initialize with no active camera stream', () => {
      const wrapper = ({ children }: { children: ReactNode }) => (
        <CameraProvider>{children}</CameraProvider>
      );

      const { result } = renderHook(() => useCamera(), { wrapper });

      expect(result.current.isCameraActive).toBe(false);
      expect(result.current.streamRef.current).toBeNull();
    });

    it('should request camera access and return stream', async () => {
      const wrapper = ({ children }: { children: ReactNode }) => (
        <CameraProvider>{children}</CameraProvider>
      );

      const { result } = renderHook(() => useCamera(), { wrapper });

      let stream: MediaStream | null = null;

      await act(async () => {
        stream = await result.current.requestCameraAccess();
      });

      expect(stream).toBeDefined();
      expect(stream).not.toBeNull();
      expect(result.current.isCameraActive).toBe(true);
      expect(result.current.streamRef.current).toBe(stream);
    });

    it('should call getUserMedia with correct constraints', async () => {
      const getUserMediaSpy = vi.spyOn(navigator.mediaDevices, 'getUserMedia');

      const wrapper = ({ children }: { children: ReactNode }) => (
        <CameraProvider>{children}</CameraProvider>
      );

      const { result } = renderHook(() => useCamera(), { wrapper });

      await act(async () => {
        await result.current.requestCameraAccess();
      });

      expect(getUserMediaSpy).toHaveBeenCalledWith({
        video: {
          facingMode: 'environment',
          width: { ideal: 1920 },
          height: { ideal: 1080 },
        },
        audio: false,
      });
    });

    it('should reuse existing active stream instead of creating new one', async () => {
      const getUserMediaSpy = vi.spyOn(navigator.mediaDevices, 'getUserMedia');

      const wrapper = ({ children }: { children: ReactNode }) => (
        <CameraProvider>{children}</CameraProvider>
      );

      const { result } = renderHook(() => useCamera(), { wrapper });

      // First request
      let firstStream: MediaStream | null = null;
      await act(async () => {
        firstStream = await result.current.requestCameraAccess();
      });

      expect(getUserMediaSpy).toHaveBeenCalledTimes(1);
      expect(firstStream).not.toBeNull();

      // Second request should reuse existing stream
      let secondStream: MediaStream | null = null;
      await act(async () => {
        secondStream = await result.current.requestCameraAccess();
      });

      // getUserMedia should not be called again
      expect(getUserMediaSpy).toHaveBeenCalledTimes(1);
      expect(secondStream).toBe(firstStream);
      expect(result.current.isCameraActive).toBe(true);
    });

    it('should create new stream if previous one was stopped', async () => {
      const getUserMediaSpy = vi.spyOn(navigator.mediaDevices, 'getUserMedia');

      const wrapper = ({ children }: { children: ReactNode }) => (
        <CameraProvider>{children}</CameraProvider>
      );

      const { result } = renderHook(() => useCamera(), { wrapper });

      // First request
      await act(async () => {
        await result.current.requestCameraAccess();
      });

      expect(getUserMediaSpy).toHaveBeenCalledTimes(1);

      // Stop the camera
      act(() => {
        result.current.stopCamera();
      });

      expect(result.current.isCameraActive).toBe(false);

      // Second request should create new stream
      await act(async () => {
        await result.current.requestCameraAccess();
      });

      expect(getUserMediaSpy).toHaveBeenCalledTimes(2);
      expect(result.current.isCameraActive).toBe(true);
    });
  });

  describe('Camera stream cleanup', () => {
    it('should stop all tracks when stopCamera is called', async () => {
      const wrapper = ({ children }: { children: ReactNode }) => (
        <CameraProvider>{children}</CameraProvider>
      );

      const { result } = renderHook(() => useCamera(), { wrapper });

      await act(async () => {
        await result.current.requestCameraAccess();
      });

      const stream = result.current.streamRef.current;
      expect(stream).not.toBeNull();

      const tracks = stream!.getTracks();
      const stopSpy = vi.spyOn(tracks[0], 'stop');

      act(() => {
        result.current.stopCamera();
      });

      expect(stopSpy).toHaveBeenCalled();
      expect(result.current.streamRef.current).toBeNull();
      expect(result.current.isCameraActive).toBe(false);
    });

    it('should handle stopCamera when no stream exists', () => {
      const wrapper = ({ children }: { children: ReactNode }) => (
        <CameraProvider>{children}</CameraProvider>
      );

      const { result } = renderHook(() => useCamera(), { wrapper });

      expect(() => {
        act(() => {
          result.current.stopCamera();
        });
      }).not.toThrow();

      expect(result.current.isCameraActive).toBe(false);
    });

    it('should cleanup stream on unmount', async () => {
      const wrapper = ({ children }: { children: ReactNode }) => (
        <CameraProvider>{children}</CameraProvider>
      );

      const { result, unmount } = renderHook(() => useCamera(), { wrapper });

      await act(async () => {
        await result.current.requestCameraAccess();
      });

      const stream = result.current.streamRef.current;
      expect(stream).not.toBeNull();

      const tracks = stream!.getTracks();
      const stopSpy = vi.spyOn(tracks[0], 'stop');

      unmount();

      expect(stopSpy).toHaveBeenCalled();
    });

    it('should set isCameraActive to false when track ends', async () => {
      const wrapper = ({ children }: { children: ReactNode }) => (
        <CameraProvider>{children}</CameraProvider>
      );

      const { result } = renderHook(() => useCamera(), { wrapper });

      await act(async () => {
        await result.current.requestCameraAccess();
      });

      expect(result.current.isCameraActive).toBe(true);

      const stream = result.current.streamRef.current;
      const track = stream!.getTracks()[0];

      // Simulate track ending (e.g., user revokes permission)
      act(() => {
        track.stop();
      });

      await waitFor(() => {
        expect(result.current.isCameraActive).toBe(false);
      });

      expect(result.current.streamRef.current).toBeNull();
    });
  });

  describe('Error handling', () => {
    it('should handle getUserMedia errors gracefully', async () => {
      const getUserMediaSpy = vi
        .spyOn(navigator.mediaDevices, 'getUserMedia')
        .mockRejectedValueOnce(new Error('Camera permission denied'));

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      const wrapper = ({ children }: { children: ReactNode }) => (
        <CameraProvider>{children}</CameraProvider>
      );

      const { result } = renderHook(() => useCamera(), { wrapper });

      let stream: MediaStream | null = null;

      await act(async () => {
        stream = await result.current.requestCameraAccess();
      });

      expect(stream).toBeNull();
      expect(result.current.isCameraActive).toBe(false);
      expect(consoleSpy).toHaveBeenCalledWith(
        '[CameraContext] Error accessing camera:',
        expect.any(Error)
      );

      getUserMediaSpy.mockRestore();
      consoleSpy.mockRestore();
    });

    it('should return null and log error on camera access failure', async () => {
      const error = new DOMException('Permission denied', 'NotAllowedError');

      vi.spyOn(navigator.mediaDevices, 'getUserMedia').mockRejectedValueOnce(error);

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      const wrapper = ({ children }: { children: ReactNode }) => (
        <CameraProvider>{children}</CameraProvider>
      );

      const { result } = renderHook(() => useCamera(), { wrapper });

      let stream: MediaStream | null = null;

      await act(async () => {
        stream = await result.current.requestCameraAccess();
      });

      expect(stream).toBeNull();
      expect(result.current.isCameraActive).toBe(false);
      expect(result.current.streamRef.current).toBeNull();

      consoleSpy.mockRestore();
    });
  });

  describe('Context state management', () => {
    it('should provide consistent stream reference', async () => {
      const getUserMediaSpy = vi.spyOn(navigator.mediaDevices, 'getUserMedia');
      getUserMediaSpy.mockClear();

      const wrapper = ({ children }: { children: ReactNode }) => (
        <CameraProvider>{children}</CameraProvider>
      );

      const { result } = renderHook(() => useCamera(), { wrapper });

      await act(async () => {
        await result.current.requestCameraAccess();
      });

      // Stream reference should be consistent
      const firstStream = result.current.streamRef.current;
      const secondStream = result.current.streamRef.current;

      expect(firstStream).toBe(secondStream);
      expect(firstStream).not.toBeNull();

      getUserMediaSpy.mockRestore();
    });

    it('should update state when stopping camera', async () => {
      const wrapper = ({ children }: { children: ReactNode }) => (
        <CameraProvider>{children}</CameraProvider>
      );

      const { result } = renderHook(() => useCamera(), { wrapper });

      // Request camera
      await act(async () => {
        await result.current.requestCameraAccess();
      });

      const hasStream = result.current.streamRef.current !== null;
      expect(hasStream).toBe(true);

      // Stop camera
      act(() => {
        result.current.stopCamera();
      });

      expect(result.current.isCameraActive).toBe(false);
      // Stream should be cleared (null or undefined is acceptable)
      expect(result.current.streamRef.current).toBeFalsy();
    });
  });
});
