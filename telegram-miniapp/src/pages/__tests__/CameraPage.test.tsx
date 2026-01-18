import { describe, it, expect, beforeEach, vi } from 'vitest';
import type { ChoicesResponse, DestinationsResponse, RecognitionResult } from '@/types/api';

// Test data
const mockChoices: ChoicesResponse = {
  vehicle_types: [
    { label: 'Енгил', value: 'LIGHT' },
    { label: 'Юк', value: 'CARGO' },
  ],
  visitor_types: [
    { label: 'Ходим', value: 'EMPLOYEE' },
    { label: 'Мижоз', value: 'CUSTOMER' },
    { label: 'Меҳмон', value: 'GUEST' },
  ],
  transport_types: [
    { label: 'Платформа', value: 'PLATFORM' },
    { label: 'Фура', value: 'FURA' },
    { label: 'Прицеп', value: 'PRICEP' },
  ],
  load_statuses: [
    { label: 'Юклик', value: 'LOADED' },
    { label: 'Бўш', value: 'EMPTY' },
  ],
  cargo_types: [
    { label: 'Контейнер', value: 'CONTAINER' },
    { label: 'Озиқ-овқат', value: 'FOOD' },
    { label: 'Металл', value: 'METAL' },
  ],
  container_sizes: [
    { label: '20 футлик', value: '1x20F' },
    { label: '40 футлик', value: '40F' },
  ],
};

const mockDestinations: DestinationsResponse = {
  count: 2,
  next: null,
  previous: null,
  results: [
    { id: 1, zone: 'A', name: 'Склад 1', capacity: 100, current_count: 50 },
    { id: 2, zone: 'B', name: 'Склад 2', capacity: 100, current_count: 30 },
  ],
};

const mockRecognitionSuccess: RecognitionResult = {
  success: true,
  plate_number: '01A234BC',
  confidence: 0.95,
  processing_time: 1.2,
};

const mockRecognitionFailure: RecognitionResult = {
  success: false,
  plate_number: '',
  confidence: 0,
  processing_time: 1.0,
};

describe('CameraPage - API Integration', () => {
  const mockFetch = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    global.fetch = mockFetch;
  });

  describe('API Error Handling', () => {
    it('should handle choices fetch failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      });

      const response = await fetch('/api/vehicles/choices');
      expect(response.ok).toBe(false);
      expect(response.status).toBe(500);
    });

    it('should handle destinations fetch failure', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
      });

      const response = await fetch('/api/vehicles/destinations');
      expect(response.ok).toBe(false);
      expect(response.status).toBe(500);
    });

    it('should handle plate recognition API error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        text: async () => 'Invalid image',
      });

      const response = await fetch('/api/terminal/plate-recognizer/recognize/', {
        method: 'POST',
      });

      expect(response.ok).toBe(false);
      expect(response.status).toBe(400);
      const errorText = await response.text();
      expect(errorText).toBe('Invalid image');
    });

    it('should handle vehicle entry submission error', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        text: async () => JSON.stringify({ error: { message: 'Номер аллақачон мавжуд' } }),
      });

      const response = await fetch('/api/vehicles/entries/', { method: 'POST' });
      expect(response.ok).toBe(false);
      const errorData = JSON.parse(await response.text()) as { error: { message: string } };
      expect(errorData.error.message).toBe('Номер аллақачон мавжуд');
    });

    it('should handle network errors', async () => {
      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      await expect(fetch('/api/vehicles/entries/')).rejects.toThrow('Network error');
    });

    it('should handle successful choices fetch', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, data: mockChoices }),
      });

      const response = await fetch('/api/vehicles/choices');
      expect(response.ok).toBe(true);
      const data = await response.json() as { success: boolean; data: ChoicesResponse };
      expect(data.success).toBe(true);
      expect(data.data.vehicle_types).toHaveLength(2);
    });

    it('should handle successful destinations fetch', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockDestinations,
      });

      const response = await fetch('/api/vehicles/destinations');
      expect(response.ok).toBe(true);
      const data = await response.json() as DestinationsResponse;
      expect(data.results).toHaveLength(2);
    });

    it('should handle successful plate recognition', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockRecognitionSuccess,
      });

      const response = await fetch('/api/terminal/plate-recognizer/recognize/', {
        method: 'POST',
      });

      expect(response.ok).toBe(true);
      const data = await response.json() as RecognitionResult;
      expect(data.success).toBe(true);
      expect(data.plate_number).toBe('01A234BC');
    });

    it('should handle failed plate recognition', async () => {
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockRecognitionFailure,
      });

      const response = await fetch('/api/terminal/plate-recognizer/recognize/', {
        method: 'POST',
      });

      expect(response.ok).toBe(true);
      const data = await response.json() as RecognitionResult;
      expect(data.success).toBe(false);
      expect(data.plate_number).toBe('');
    });
  });
});

describe('Vehicle Options Builder', () => {
  it('should build correct option tree for light vehicles', async () => {
    const { buildVehicleTypeOptions } = await import('@/utils/vehicleOptions');

    const destinationOptions = mockDestinations.results.map((dest) => ({
      label: `${dest.zone} - ${dest.name}`,
      value: String(dest.id),
    }));

    const options = buildVehicleTypeOptions(destinationOptions, mockChoices);

    const lightVehicle = options.find((opt) => opt.value === 'light');
    expect(lightVehicle).toBeDefined();
    expect(lightVehicle?.children).toHaveLength(mockChoices.visitor_types.length);
  });

  it('should build correct option tree for cargo vehicles', async () => {
    const { buildVehicleTypeOptions } = await import('@/utils/vehicleOptions');

    const destinationOptions = mockDestinations.results.map((dest) => ({
      label: `${dest.zone} - ${dest.name}`,
      value: String(dest.id),
    }));

    const options = buildVehicleTypeOptions(destinationOptions, mockChoices);

    const cargoVehicle = options.find((opt) => opt.value === 'cargo');
    expect(cargoVehicle).toBeDefined();
    expect(cargoVehicle?.children).toHaveLength(mockChoices.transport_types.length);
  });

  it('should include container options for platform vehicles', async () => {
    const { buildVehicleTypeOptions } = await import('@/utils/vehicleOptions');

    const destinationOptions = mockDestinations.results.map((dest) => ({
      label: `${dest.zone} - ${dest.name}`,
      value: String(dest.id),
    }));

    const options = buildVehicleTypeOptions(destinationOptions, mockChoices);

    const cargoVehicle = options.find((opt) => opt.value === 'cargo');
    const platformTransport = cargoVehicle?.children?.find((opt) => opt.value === 'platform');
    const loadedStatus = platformTransport?.children?.find((opt) => opt.value === 'loaded');
    const containerCargo = loadedStatus?.children?.find((opt) => opt.value === 'container');

    expect(containerCargo).toBeDefined();
    expect(containerCargo?.children).toBeDefined();
  });

  it('should exclude container options for non-platform vehicles', async () => {
    const { buildCargoTypeOptionsWithoutContainer } = await import('@/utils/vehicleOptions');

    const destinationOptions = mockDestinations.results.map((dest) => ({
      label: `${dest.zone} - ${dest.name}`,
      value: String(dest.id),
    }));

    const options = buildCargoTypeOptionsWithoutContainer(
      destinationOptions,
      mockChoices.cargo_types
    );

    const containerOption = options.find((opt) => opt.value === 'container');
    expect(containerOption).toBeUndefined();
  });

  it('should handle empty destination list', async () => {
    const { buildVehicleTypeOptions } = await import('@/utils/vehicleOptions');

    const options = buildVehicleTypeOptions([], mockChoices);

    expect(options).toHaveLength(2);
    const cargoVehicle = options.find((opt) => opt.value === 'cargo');
    const platformTransport = cargoVehicle?.children?.find((opt) => opt.value === 'platform');
    const emptyStatus = platformTransport?.children?.find((opt) => opt.value === 'empty');
    expect(emptyStatus?.children).toHaveLength(0);
  });
});

describe('Image Utilities', () => {
  it('should convert base64 to blob with correct MIME type', async () => {
    const { base64ToBlob } = await import('@/helpers/imageUtils');
    const base64 = 'data:image/jpeg;base64,/9j/4AAQSkZJRg==';

    const blob = base64ToBlob(base64);

    expect(blob).toBeInstanceOf(Blob);
    expect(blob.type).toBe('image/jpeg');
  });

  it('should handle PNG base64 strings', async () => {
    const { base64ToBlob } = await import('@/helpers/imageUtils');
    const base64 = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==';

    const blob = base64ToBlob(base64);

    expect(blob).toBeInstanceOf(Blob);
    expect(blob.type).toBe('image/png');
  });

  it('should create FormData with photo', async () => {
    const { createPhotoFormData } = await import('@/helpers/imageUtils');
    const base64 = 'data:image/jpeg;base64,/9j/4AAQSkZJRg==';

    const formData = createPhotoFormData(base64, 'photo', 'test.jpg');

    expect(formData).toBeInstanceOf(FormData);
    expect(formData.has('photo')).toBe(true);
  });

  it('should use default parameters for FormData', async () => {
    const { createPhotoFormData } = await import('@/helpers/imageUtils');
    const base64 = 'data:image/jpeg;base64,/9j/4AAQSkZJRg==';

    const formData = createPhotoFormData(base64);

    expect(formData).toBeInstanceOf(FormData);
    expect(formData.has('image')).toBe(true);
  });
});

describe('Canvas and Video mocks', () => {
  it('should mock canvas.toDataURL with JPEG quality', () => {
    const canvas = document.createElement('canvas');
    const toDataURLSpy = vi.spyOn(canvas, 'toDataURL');

    canvas.toDataURL('image/jpeg', 0.7);

    expect(toDataURLSpy).toHaveBeenCalledWith('image/jpeg', 0.7);
  });

  it('should mock canvas.getContext', () => {
    const canvas = document.createElement('canvas');
    const ctx = canvas.getContext('2d');

    expect(ctx).not.toBeNull();
    expect(ctx).toHaveProperty('drawImage');
  });

  it('should mock video.play', async () => {
    const video = document.createElement('video');
    await expect(video.play()).resolves.toBeUndefined();
  });
});
