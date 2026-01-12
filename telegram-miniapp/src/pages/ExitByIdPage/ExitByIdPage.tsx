import type { FC } from 'react';
import { useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Button, Card, Dialog, Grid, Image, Input, Radio, Space, Toast, Loading } from 'antd-mobile';
import { X, Camera } from 'lucide-react';

import { Page } from '@/components/Page.tsx';
import { CameraOverlay } from '@/components/CameraOverlay';
import { useCamera } from '@/contexts/CameraContext';
import { usePlateRecognition } from '@/hooks/usePlateRecognition';
import { base64ToBlob, capturePhotoFromVideo } from '@/helpers/imageUtils';
import { API_ENDPOINTS } from '@/config/api';
import type { VehicleEntry, LoadStatus } from '@/types/api';

export const ExitByIdPage: FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { requestCameraAccess } = useCamera();
  const {
    isRecognizing,
    plateNumber,
    setPlateNumber,
    recognizePlate,
    reset: resetRecognition,
  } = usePlateRecognition({ showToastOnFailure: false });

  // Vehicle data state
  const [vehicleData, setVehicleData] = useState<VehicleEntry | null>(null);
  const [isLoadingVehicle, setIsLoadingVehicle] = useState(true);

  // Camera state
  const [isCameraOpen, setIsCameraOpen] = useState(false);
  const [isCameraLoading, setIsCameraLoading] = useState(false);
  const [isSubmittingExit, setIsSubmittingExit] = useState(false);
  const [capturedPhoto, setCapturedPhoto] = useState<string | null>(null);
  const [exitLoadStatus, setExitLoadStatus] = useState<LoadStatus>('EMPTY');
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);

  // Fetch vehicle data on mount
  useEffect(() => {
    if (id) {
      void fetchVehicleData(id);
    }
  }, [id]);

  const fetchVehicleData = async (vehicleId: string) => {
    setIsLoadingVehicle(true);
    try {
      const response = await fetch(API_ENDPOINTS.vehicles.entry(Number(vehicleId)), {
        method: 'GET',
        headers: {
          'Accept': 'application/json',
        },
      });

      if (!response.ok) {
        Toast.show({ content: 'Маълумот топилмади', icon: 'fail' });
        navigate('/vehicles');
        return;
      }

      const data = await response.json() as VehicleEntry;
      setVehicleData(data);
    } catch (error) {
      console.error('Error fetching vehicle:', error);
      Toast.show({ content: 'Хатолик юз берди', icon: 'fail' });
      navigate('/vehicles');
    } finally {
      setIsLoadingVehicle(false);
    }
  };

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
      const result = await recognizePlate(imageData);

      if (result?.success) {
        // Compare recognized plate with vehicle's license plate
        const recognizedPlate = result.plate_number.replace(/\s+/g, '').toUpperCase();
        const vehiclePlate = (vehicleData?.license_plate || '').replace(/\s+/g, '').toUpperCase();

        if (vehiclePlate && recognizedPlate !== vehiclePlate) {
          Toast.show({
            content: `Рақам мос келмади! Аниқланган: ${result.plate_number}, Кутилган: ${vehicleData?.license_plate}`,
            icon: 'fail',
            duration: 3000,
          });
        }
      } else {
        Toast.show({
          content: 'Рақам аниқланмади. Илтимос, қўлда киритинг',
          icon: 'fail',
          duration: 2000,
        });
      }
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

  const submitExit = async () => {
    if (!capturedPhoto) {
      Toast.show({ content: 'Илтимос, расм олинг', icon: 'fail' });
      return;
    }

    if (!plateNumber.trim()) {
      Toast.show({ content: 'Илтимос, давлат рақамини киритинг', icon: 'fail' });
      return;
    }

    setIsSubmittingExit(true);

    try {
      const formData = new FormData();

      formData.append('license_plate', plateNumber.trim());
      formData.append('exit_time', new Date().toISOString());
      formData.append('exit_load_status', exitLoadStatus);

      const blob = base64ToBlob(capturedPhoto);
      formData.append('exit_photo_files', blob, 'exit_photo_1.jpg');

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
      console.error('Error submitting exit:', error);
      Toast.show({ content: 'Хатолик: ' + (error instanceof Error ? error.message : 'Unknown'), icon: 'fail' });
    } finally {
      setIsSubmittingExit(false);
    }
  };

  if (isLoadingVehicle) {
    return (
      <Page back={true} onBack={() => navigate('/vehicles')} title="Чиқариш">
        <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
          <Loading color="primary" />
        </div>
      </Page>
    );
  }

  return (
    <>
      {!isCameraOpen ? (
        <Page back={true} onBack={handleBackNavigation} title="Чиқариш">
          <Space direction='vertical' block style={{ padding: '10px', paddingBottom: '100px' }}>
            {/* Vehicle Info Card */}
            {vehicleData && (
              <Card title="Машина маълумотлари">
                <Grid columns={1} gap={16}>
                  <Grid.Item>
                    <div className='text-base'>{vehicleData.license_plate}</div>
                    <div className='text-sm' style={{ color: '#999' }}>Давлат рақами</div>
                  </Grid.Item>
                  {vehicleData.customer && (
                    <Grid.Item>
                      <div className='text-base'>{vehicleData.customer.name} ({vehicleData.customer.phone})</div>
                      <div className='text-sm' style={{ color: '#999' }}>Мижоз / Телефон</div>
                    </Grid.Item>
                  )}
                </Grid>
              </Card>
            )}

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
                onClick={submitExit}
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
