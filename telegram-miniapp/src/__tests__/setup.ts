import '@testing-library/jest-dom';
import { afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';

// Cleanup after each test
afterEach(() => {
  cleanup();
});

// Mock MediaDevices API for camera tests
class MockMediaStream {
  private tracks: MediaStreamTrack[];
  active: boolean;

  constructor() {
    this.tracks = [new MockMediaStreamTrack()];
    this.active = true;
  }

  getTracks(): MediaStreamTrack[] {
    return this.tracks || [];
  }

  getVideoTracks(): MediaStreamTrack[] {
    return this.tracks || [];
  }

  getAudioTracks(): MediaStreamTrack[] {
    return [];
  }

  addTrack(track: MediaStreamTrack): void {
    if (!this.tracks) {
      this.tracks = [];
    }
    this.tracks.push(track);
  }

  removeTrack(track: MediaStreamTrack): void {
    if (!this.tracks) return;
    const index = this.tracks.indexOf(track);
    if (index !== -1) {
      this.tracks.splice(index, 1);
    }
  }

  getTrackById(): MediaStreamTrack | null {
    return null;
  }

  clone(): MediaStream {
    return new MockMediaStream() as unknown as MediaStream;
  }

  addEventListener(): void {}
  removeEventListener(): void {}
  dispatchEvent(): boolean {
    return true;
  }
}

class MockMediaStreamTrack implements MediaStreamTrack {
  enabled = true;
  id = 'mock-track-id';
  kind: 'video' | 'audio' = 'video';
  label = 'Mock Camera';
  muted = false;
  readonly = false;
  readyState: 'live' | 'ended' = 'live';
  remote = false;
  onended: ((this: MediaStreamTrack, ev: Event) => unknown) | null = null;
  onmute: ((this: MediaStreamTrack, ev: Event) => unknown) | null = null;
  onunmute: ((this: MediaStreamTrack, ev: Event) => unknown) | null = null;
  contentHint = '';
  isolated = false;

  clone(): MediaStreamTrack {
    return new MockMediaStreamTrack();
  }

  stop(): void {
    this.readyState = 'ended';
    if (this.onended) {
      this.onended.call(this, new Event('ended'));
    }
  }

  getCapabilities(): MediaTrackCapabilities {
    return {};
  }

  getConstraints(): MediaTrackConstraints {
    return {};
  }

  getSettings(): MediaTrackSettings {
    return {
      width: 1920,
      height: 1080,
      deviceId: 'mock-device',
      facingMode: 'environment',
    };
  }

  applyConstraints(): Promise<void> {
    return Promise.resolve();
  }

  addEventListener(): void {}
  removeEventListener(): void {}
  dispatchEvent(): boolean {
    return true;
  }
}

// Mock navigator.mediaDevices
Object.defineProperty(global.navigator, 'mediaDevices', {
  writable: true,
  value: {
    getUserMedia: vi.fn().mockImplementation(() =>
      Promise.resolve(new MockMediaStream() as unknown as MediaStream)
    ),
    enumerateDevices: vi.fn().mockResolvedValue([]),
    getSupportedConstraints: vi.fn().mockReturnValue({}),
    getDisplayMedia: vi.fn(),
  },
});

// Mock HTMLCanvasElement
HTMLCanvasElement.prototype.getContext = vi.fn().mockReturnValue({
  drawImage: vi.fn(),
  clearRect: vi.fn(),
  fillRect: vi.fn(),
  canvas: {},
}) as unknown as typeof HTMLCanvasElement.prototype.getContext;

HTMLCanvasElement.prototype.toDataURL = vi.fn().mockReturnValue('data:image/jpeg;base64,mock-image-data');

// Mock HTMLVideoElement
Object.defineProperty(HTMLVideoElement.prototype, 'play', {
  writable: true,
  value: vi.fn().mockResolvedValue(undefined),
});

Object.defineProperty(HTMLVideoElement.prototype, 'pause', {
  writable: true,
  value: vi.fn(),
});

// Mock fetch globally
global.fetch = vi.fn();

// Export mock utilities for tests
export { MockMediaStream, MockMediaStreamTrack };
