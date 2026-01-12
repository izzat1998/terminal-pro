import type { FC } from 'react';
import { useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Card, Dialog, Image, Input, Loading, Radio, Space, Toast } from 'antd-mobile';
import { X, Camera } from 'lucide-react';

import { Page } from '@/components/Page.tsx';
import { CameraOverlay } from '@/components/CameraOverlay';
import { useCamera } from '@/contexts/CameraContext';
import { usePlateRecognition } from '@/hooks/usePlateRecognition';
import { base64ToBlob, capturePhotoFromVideo } from '@/helpers/imageUtils';
import { API_ENDPOINTS } from '@/config/api';
import type { LoadStatus } from '@/types/api';

export const ExitEntryPage: FC = () => {
  const navigate = useNavigate();
  const { requestCameraAccess } = useCamera();
  const {
    isRecognizing,
    plateNumber,
    setPlateNumber,
    recognizePlate,
    reset: resetRecognition,
  } = usePlateRecognition();

  // Camera state
  const [isCameraOpen, setIsCameraOpen] = useState(false);
  const [isCameraLoading, setIsCameraLoading] = useState(false);
  const [isSubmittingExit, setIsSubmittingExit] = useState(false);
  const [capturedPhoto, setCapturedPhoto] = useState<string | null>(null);
  const [exitLoadStatus, setExitLoadStatus] = useState<LoadStatus>('EMPTY');
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  const openCamera = async () => {
    try {
      setIsCameraOpen(true);
      setIsCameraLoading(true);

      await new Promise(resolve => setTimeout(resolve, 150));

      const stream = await requestCameraAccess();

      if (!stream) {
        throw new Error('Failed to get camera stream');
      }

      if (videoRef.current) {
        videoRef.current.srcObject = stream;

        try {
          await videoRef.current.play();
          setIsCameraLoading(false);
        } catch (playError) {
          console.error('Error playing video:', playError);
          setIsCameraLoading(false);
        }
      } else {
        setIsCameraLoading(false);
        throw new Error('Video element not found');
      }
    } catch (error) {
      console.error('Error accessing camera:', error);
      setIsCameraLoading(false);
      setIsCameraOpen(false);
      void Dialog.alert({
        content: `Камерага кириш имкони бўлмади: ${error instanceof Error ? error.message : 'Unknown error'}`,
        confirmText: 'OK',
      });
    }
  };

  const capturePhoto = (): string | null => {
    if (videoRef.current && canvasRef.current) {
      const imageData = capturePhotoFromVideo(videoRef.current, canvasRef.current);
      if (imageData) {
        setCapturedPhoto(imageData);
        setIsCameraOpen(false);
        return imageData;
      }
    }
    return null;
  };

  const deletePhoto = () => {
    setCapturedPhoto(null);
    resetRecognition();
  };

  const handleCameraCapture = async () => {
    const imageData = capturePhoto();
    if (imageData) {
      await recognizePlate(imageData);
    }
  };

  const goBack = () => {
    setIsCameraOpen(false);
  };

  const handleBackNavigation = () => {
    if (isCameraOpen) {
      goBack();
    } else {
      navigate('/vehicles');
    }
  };

  const submitExitEntry = async () => {
    if (!capturedPhoto) {
      Toast.show({ content: 'Илтимос, расм олинг', icon: 'fail' });
      return;
    }

    if (!plateNumber.trim()) {
      Toast.show({ content: 'Илтимос, номер киритинг', icon: 'fail' });
      return;
    }

    setIsSubmittingExit(true);

    try {
      const formData = new FormData();

      // Add photo file
      const blob = base64ToBlob(capturedPhoto);
      formData.append('exit_photo_files', blob, 'exit_photo_1.jpg');

      // Add license plate
      formData.append('license_plate', plateNumber.trim());

      // Add exit time
      formData.append('exit_time', new Date().toISOString());

      // Add exit load status
      formData.append('exit_load_status', exitLoadStatus);

      const response = await fetch(`${API_ENDPOINTS.vehicles.entries}exit/`, {
        method: 'POST',
        headers: {
          'Accept': 'application/json',
        },
        body: formData,
      });

      if (!response.ok) {
        const errorText = await response.text();
        console.error('API error response:', errorText);

        try {
          const errorJson = JSON.parse(errorText) as { error?: { message?: string } };
          const errorMessage = errorJson.error?.message || 'Хатолик юз берди';
          Toast.show({ content: errorMessage, icon: 'fail', duration: 3000 });
        } catch {
          Toast.show({ content: 'Хатолик юз берди', icon: 'fail' });
        }
        return;
      }

      Toast.show({ content: 'Муваффақиятли чиқарилди!', icon: 'success' });

      setTimeout(() => {
        navigate('/vehicles');
      }, 1000);
    } catch (error) {
      console.error('Error submitting exit entry:', error);
      Toast.show({ content: 'Хатолик: ' + (error instanceof Error ? error.message : 'Unknown'), icon: 'fail' });
    } finally {
      setIsSubmittingExit(false);
    }
  };

  return (
    <>
      {!isCameraOpen ? (
        <Page back={true} onBack={handleBackNavigation} title="Терминалдан чиқариш">
          <Space direction='vertical' block style={{ padding: '10px', paddingBottom: '100px' }}>
            <Card title="Расм">
              {capturedPhoto ? (
                <div className='relative' style={{ display: 'inline-block' }}>
                  <Image
                    className='rounded'
                    fit={'cover'}
                    width={150}
                    height={150}
                    src={capturedPhoto}
                  />
                  <div
                    onClick={deletePhoto}
                    className='absolute top-1 right-1 bg-red-500 rounded-full p-1 cursor-pointer'
                  >
                    <X size={14} color='white' />
                  </div>
                </div>
              ) : (
                <Button block onClick={openCamera}>
                  <Camera size={18} style={{ marginRight: 8, display: 'inline' }} />
                  Расм олиш
                </Button>
              )}
            </Card>

            {/* Plate Number Card - shown after photo is captured */}
            {capturedPhoto && (
              <Card title="Давлат рақами">
                {isRecognizing ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <Loading color="primary" />
                    <span style={{ color: '#999' }}>Рақам аниқланмоқда...</span>
                  </div>
                ) : (
                  <Input
                    value={plateNumber}
                    onChange={setPlateNumber}
                    placeholder="Давлат рақамини киритинг"
                    clearable
                  />
                )}
              </Card>
            )}

            {/* Load Status Card - shown after photo is captured and recognition is done */}
            {capturedPhoto && !isRecognizing && (
              <Card title="Юк ҳолати">
                <Radio.Group value={exitLoadStatus} onChange={(val) => setExitLoadStatus(val as LoadStatus)}>
                  <Space direction='vertical' block>
                    <Radio value='EMPTY'>Бўш</Radio>
                    <Radio value='LOADED'>Юкланган</Radio>
                  </Space>
                </Radio.Group>
              </Card>
            )}

            {capturedPhoto && plateNumber.trim() && !isRecognizing && (
              <Button
                block
                color='danger'
                size='large'
                onClick={submitExitEntry}
                loading={isSubmittingExit}
                disabled={isSubmittingExit}
              >
                {isSubmittingExit ? 'Чиқарилмоқда...' : 'Чиқариш'}
              </Button>
            )}
          </Space>
        </Page>
      ) : null}

      {isCameraOpen && (
        <Page back={true} onBack={handleBackNavigation} title="Камера">
          <CameraOverlay
            videoRef={videoRef}
            canvasRef={canvasRef}
            isLoading={isCameraLoading}
            onCancel={goBack}
            onCapture={handleCameraCapture}
          />
        </Page>
      )}
    </>
  );
};
