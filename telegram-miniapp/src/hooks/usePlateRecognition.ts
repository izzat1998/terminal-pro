/**
 * Hook for license plate recognition using the API
 * Consolidates plate recognition logic from multiple camera pages
 */

import { useState, useCallback } from 'react';
import { Toast } from 'antd-mobile';
import type { RecognitionResult } from '@/types/api';
import { base64ToBlob } from '@/helpers/imageUtils';
import { API_ENDPOINTS } from '@/config/api';

interface UsePlateRecognitionReturn {
  /** Whether recognition is in progress */
  isRecognizing: boolean;
  /** Last recognition result */
  result: RecognitionResult | null;
  /** Recognized plate number (empty if not recognized) */
  plateNumber: string;
  /** Manually set the plate number */
  setPlateNumber: (value: string) => void;
  /** Recognize a plate from a base64 image */
  recognizePlate: (imageData: string) => Promise<RecognitionResult | null>;
  /** Reset the recognition state */
  reset: () => void;
}

interface UsePlateRecognitionOptions {
  /** Region for plate recognition (default: 'uz') */
  region?: string;
  /** Whether to show toast on failure (default: true) */
  showToastOnFailure?: boolean;
  /** Custom failure message */
  failureMessage?: string;
}

/**
 * Hook for handling license plate recognition
 *
 * @example
 * ```tsx
 * const { isRecognizing, plateNumber, setPlateNumber, recognizePlate } = usePlateRecognition();
 *
 * const handleCapture = async (imageData: string) => {
 *   await recognizePlate(imageData);
 * };
 * ```
 */
export function usePlateRecognition(
  options: UsePlateRecognitionOptions = {}
): UsePlateRecognitionReturn {
  const {
    region = 'uz',
    showToastOnFailure = true,
    failureMessage = 'Рақам аниқланмади. Илтимос, қўлда киритинг',
  } = options;

  const [isRecognizing, setIsRecognizing] = useState(false);
  const [result, setResult] = useState<RecognitionResult | null>(null);
  const [plateNumber, setPlateNumber] = useState('');

  const recognizePlate = useCallback(
    async (imageData: string): Promise<RecognitionResult | null> => {
      setIsRecognizing(true);
      setResult(null);

      try {
        const blob = base64ToBlob(imageData);
        const formData = new FormData();
        formData.append('image', blob, 'plate.jpg');
        formData.append('region', region);

        const response = await fetch(API_ENDPOINTS.terminal.plateRecognizer, {
          method: 'POST',
          headers: {
            'Accept': 'application/json',
          },
          body: formData,
        });

        if (!response.ok) {
          console.error('Plate recognition API error:', response.status);
          if (showToastOnFailure) {
            Toast.show({
              content: failureMessage,
              icon: 'fail',
              duration: 2000,
            });
          }
          return null;
        }

        const recognitionResult = (await response.json()) as RecognitionResult;
        setResult(recognitionResult);

        if (recognitionResult.success) {
          setPlateNumber(recognitionResult.plate_number);
        } else if (showToastOnFailure) {
          Toast.show({
            content: failureMessage,
            icon: 'fail',
            duration: 2000,
          });
        }

        return recognitionResult;
      } catch (error) {
        console.error('Error recognizing plate:', error);
        if (showToastOnFailure) {
          Toast.show({
            content: failureMessage,
            icon: 'fail',
            duration: 2000,
          });
        }
        return null;
      } finally {
        setIsRecognizing(false);
      }
    },
    [region, showToastOnFailure, failureMessage]
  );

  const reset = useCallback(() => {
    setResult(null);
    setPlateNumber('');
  }, []);

  return {
    isRecognizing,
    result,
    plateNumber,
    setPlateNumber,
    recognizePlate,
    reset,
  };
}
