/**
 * Three.js scene setup composable
 * Features: Light theme, shadows, ground markings
 */

import { ref, shallowRef, onUnmounted, type Ref } from 'vue';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { ZONE_LAYOUT, SPACING } from '../types/placement';
import type { ZoneCode } from '../types/placement';

// Camera preset types
export type CameraPreset = 'isometric' | 'top' | 'front' | 'side';

export function use3DScene(canvasRef: Ref<HTMLCanvasElement | undefined>) {
  const scene = shallowRef<THREE.Scene>();
  const camera = shallowRef<THREE.OrthographicCamera>();
  const renderer = shallowRef<THREE.WebGLRenderer>();
  const controls = shallowRef<OrbitControls>();
  const isInitialized = ref(false);
  const currentPreset = ref<CameraPreset>('isometric');
  let animationId: number | null = null;

  function initScene(): void {
    if (!canvasRef.value || isInitialized.value) return;

    // Scene - Light theme
    scene.value = new THREE.Scene();
    scene.value.background = new THREE.Color(0xf0f2f5);

    // Camera (orthographic for bird's-eye view)
    // Zone A only: X ~130m (10 bays × 13.0m), Z ~30m (10 rows × 3.0m)
    // Frustum sized to fit the wider zone
    const aspect = canvasRef.value.clientWidth / canvasRef.value.clientHeight;
    const frustumSize = 90; // Fits wider zone (130m × 30m)
    camera.value = new THREE.OrthographicCamera(
      -frustumSize * aspect / 2,
      frustumSize * aspect / 2,
      frustumSize / 2,
      -frustumSize / 2,
      0.1,
      500
    );
    // Center camera on Zone A (130m/2 = 65, 30m/2 = 15)
    camera.value.position.set(65, 60, 50);
    camera.value.lookAt(65, 0, 15);

    // Renderer with shadow support
    renderer.value = new THREE.WebGLRenderer({
      canvas: canvasRef.value,
      antialias: true,
    });
    renderer.value.setSize(canvasRef.value.clientWidth, canvasRef.value.clientHeight);
    renderer.value.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.value.shadowMap.enabled = true;
    renderer.value.shadowMap.type = THREE.PCFSoftShadowMap;

    // Controls - Enhanced for smoother navigation
    controls.value = new OrbitControls(camera.value, renderer.value.domElement);
    controls.value.enableDamping = true;
    controls.value.dampingFactor = 0.1;  // Increased for smoother feel
    controls.value.maxPolarAngle = Math.PI / 2.1;  // Allow slightly more vertical rotation
    controls.value.minPolarAngle = 0;

    // Enable panning (essential for navigation)
    controls.value.enablePan = true;
    controls.value.panSpeed = 1.5;  // Faster panning
    controls.value.screenSpacePanning = true;  // Pan parallel to screen (more intuitive)

    // Rotation smoothing
    controls.value.enableRotate = true;
    controls.value.rotateSpeed = 0.8;  // Slightly slower rotation for precision

    // Zoom limits for OrthographicCamera
    controls.value.minZoom = 0.2;   // Allow zooming out more
    controls.value.maxZoom = 6.0;   // Allow closer zoom
    controls.value.zoomSpeed = 1.2; // Responsive zoom

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
    scene.value.add(ambientLight);

    // Directional light with shadows
    const directionalLight = new THREE.DirectionalLight(0xffffff, 1.0);
    directionalLight.position.set(50, 80, 40);
    directionalLight.castShadow = true;

    // Shadow camera configuration (covers Zone A: 130m × 30m)
    directionalLight.shadow.mapSize.width = 2048;
    directionalLight.shadow.mapSize.height = 2048;
    directionalLight.shadow.camera.near = 10;
    directionalLight.shadow.camera.far = 300;
    directionalLight.shadow.camera.left = -20;
    directionalLight.shadow.camera.right = 150;
    directionalLight.shadow.camera.top = 50;
    directionalLight.shadow.camera.bottom = -20;
    directionalLight.shadow.bias = -0.001;

    scene.value.add(directionalLight);

    // Ground plane - Concrete/asphalt appearance
    // Zone A only: X: 0 to ~130m, Z: 0 to ~30m (with padding)
    const groundGeometry = new THREE.PlaneGeometry(160, 60);
    const groundMaterial = new THREE.MeshStandardMaterial({
      color: 0xd4d4d4,
      roughness: 0.95,
      metalness: 0.0,
    });
    const ground = new THREE.Mesh(groundGeometry, groundMaterial);
    ground.rotation.x = -Math.PI / 2;
    // Center ground under Zone A (130m/2 = 65, 30m/2 = 15)
    ground.position.set(65, -0.05, 15);
    ground.receiveShadow = true;
    scene.value.add(ground);

    // Add zone ground markings
    createZoneGroundMarkings();

    isInitialized.value = true;
    animate();
  }

  // Create colored ground areas for each zone
  function createZoneGroundMarkings(): void {
    if (!scene.value) return;

    // Currently only Zone A for simplified version
    const zones: ZoneCode[] = ['A'];
    const zoneColors: Partial<Record<ZoneCode, number>> = {
      A: 0xcce5ff, // Light blue
    };

    for (const zone of zones) {
      const layout = ZONE_LAYOUT[zone];
      if (!layout) continue; // Skip undefined zones
      const width = 10 * SPACING.bay;
      const depth = 10 * SPACING.row;

      // Zone floor marking
      const zoneGeometry = new THREE.PlaneGeometry(width, depth);
      const zoneMaterial = new THREE.MeshStandardMaterial({
        color: zoneColors[zone] ?? 0xcccccc,
        roughness: 0.9,
        metalness: 0,
        transparent: true,
        opacity: 0.6,
      });
      const zonePlane = new THREE.Mesh(zoneGeometry, zoneMaterial);
      zonePlane.rotation.x = -Math.PI / 2;
      zonePlane.position.set(
        layout.xOffset + width / 2,
        0.01,
        layout.zOffset + depth / 2
      );
      zonePlane.receiveShadow = true;
      scene.value.add(zonePlane);

      // Bay grid lines within zone
      createBayGridLines(zone, layout.xOffset, layout.zOffset, width, depth);
    }
  }

  // Create bay grid lines for a zone
  function createBayGridLines(
    _zone: ZoneCode,
    xOffset: number,
    zOffset: number,
    width: number,
    depth: number
  ): void {
    if (!scene.value) return;

    const lineMaterial = new THREE.LineBasicMaterial({
      color: 0x999999,
      transparent: true,
      opacity: 0.4,
    });

    // Vertical lines (bays)
    for (let bay = 0; bay <= 10; bay++) {
      const x = xOffset + bay * SPACING.bay;
      const points = [
        new THREE.Vector3(x, 0.02, zOffset),
        new THREE.Vector3(x, 0.02, zOffset + depth),
      ];
      const geometry = new THREE.BufferGeometry().setFromPoints(points);
      const line = new THREE.Line(geometry, lineMaterial);
      scene.value.add(line);
    }

    // Horizontal lines (rows)
    for (let row = 0; row <= 10; row++) {
      const z = zOffset + row * SPACING.row;
      const points = [
        new THREE.Vector3(xOffset, 0.02, z),
        new THREE.Vector3(xOffset + width, 0.02, z),
      ];
      const geometry = new THREE.BufferGeometry().setFromPoints(points);
      const line = new THREE.Line(geometry, lineMaterial);
      scene.value.add(line);
    }
  }

  
  function animate(): void {
    if (!renderer.value || !scene.value || !camera.value || !controls.value) return;

    animationId = requestAnimationFrame(animate);
    controls.value.update();
    renderer.value.render(scene.value, camera.value);
  }

  function handleResize(): void {
    if (!canvasRef.value || !camera.value || !renderer.value) return;

    const width = canvasRef.value.clientWidth;
    const height = canvasRef.value.clientHeight;
    const aspect = width / height;
    const frustumSize = 90; // Fits wider zone (130m × 30m)

    camera.value.left = -frustumSize * aspect / 2;
    camera.value.right = frustumSize * aspect / 2;
    camera.value.top = frustumSize / 2;
    camera.value.bottom = -frustumSize / 2;
    camera.value.updateProjectionMatrix();

    renderer.value.setSize(width, height);
  }

  // Center of Zone A (default target)
  const defaultTarget = new THREE.Vector3(65, 0, 15);

  function resetCamera(): void {
    setCameraPreset('isometric');
  }

  // Set camera to a specific preset view
  function setCameraPreset(preset: CameraPreset): void {
    if (!camera.value || !controls.value) return;

    currentPreset.value = preset;
    const target = defaultTarget.clone();

    switch (preset) {
      case 'isometric':
        // Isometric view (default) - good overview of containers
        camera.value.position.set(target.x + 40, 60, target.z + 45);
        camera.value.zoom = 1.4;  // Closer default view
        break;

      case 'top':
        // Bird's eye view - perfect for seeing layout
        camera.value.position.set(target.x, 100, target.z);
        camera.value.zoom = 1.2;
        break;

      case 'front':
        // Front view - see container stacking (tiers)
        camera.value.position.set(target.x, 20, target.z + 80);
        camera.value.zoom = 1.6;
        break;

      case 'side':
        // Side view - see bays from the side
        camera.value.position.set(target.x + 120, 20, target.z);
        camera.value.zoom = 1.6;
        break;
    }

    camera.value.lookAt(target);
    camera.value.updateProjectionMatrix();
    controls.value.target.copy(target);
    controls.value.update();
  }

  // Fit camera to show all containers in the scene (centered on actual container positions)
  function fitToContainers(): void {
    if (!camera.value || !controls.value || !scene.value) return;

    // Collect all container instance positions
    const positions: THREE.Vector3[] = [];

    scene.value.traverse((object) => {
      if (object instanceof THREE.InstancedMesh && object.count > 0) {
        const tempMatrix = new THREE.Matrix4();

        for (let i = 0; i < object.count; i++) {
          object.getMatrixAt(i, tempMatrix);
          const position = new THREE.Vector3();
          position.setFromMatrixPosition(tempMatrix);
          positions.push(position);
        }
      }
    });

    // If no containers, use default zone center
    if (positions.length === 0) {
      setCameraPreset('isometric');
      return;
    }

    // Calculate bounding box from actual container positions
    const box = new THREE.Box3();
    for (const pos of positions) {
      // Expand by container approximate size (half-extents)
      box.expandByPoint(new THREE.Vector3(pos.x - 6, pos.y - 1.5, pos.z - 1.2));
      box.expandByPoint(new THREE.Vector3(pos.x + 6, pos.y + 1.5, pos.z + 1.2));
    }

    // Calculate center and size
    const center = new THREE.Vector3();
    const size = new THREE.Vector3();
    box.getCenter(center);
    box.getSize(size);

    // Ensure minimum size for very small clusters
    size.x = Math.max(size.x, 20);
    size.z = Math.max(size.z, 10);

    // Add padding for comfortable viewing
    const padding = 1.4;
    const maxDim = Math.max(size.x, size.z) * padding;

    // Position camera for isometric view looking at container center
    const aspect = canvasRef.value!.clientWidth / canvasRef.value!.clientHeight;
    const frustumSize = 90;

    // Calculate zoom to fit all containers with some margin
    const zoomX = (frustumSize * aspect) / maxDim;
    const zoomZ = frustumSize / (size.z * padding);
    const zoom = Math.min(zoomX, zoomZ, 2.5) * 1.2;

    // Position camera for isometric view - symmetric offset for centered view
    // For orthographic camera, position determines viewing angle, not centering
    // Using equal X and Z offsets creates balanced isometric view
    const offset = Math.max(size.x, size.z) * 0.5;
    camera.value.position.set(
      center.x + offset,   // Symmetric offset
      60,
      center.z + offset    // Symmetric offset
    );
    camera.value.zoom = Math.max(zoom, 0.8);
    camera.value.lookAt(center);
    camera.value.updateProjectionMatrix();

    // CRITICAL: Set controls target to container center for proper orbit
    controls.value.target.set(center.x, center.y, center.z);
    controls.value.update();
  }

  function dispose(): void {
    if (animationId) {
      cancelAnimationFrame(animationId);
      animationId = null;
    }
    controls.value?.dispose();
    renderer.value?.dispose();
    scene.value?.clear();
    isInitialized.value = false;
  }

  onUnmounted(() => {
    dispose();
  });

  return {
    scene,
    camera,
    renderer,
    controls,
    isInitialized,
    currentPreset,
    initScene,
    handleResize,
    resetCamera,
    setCameraPreset,
    fitToContainers,
    dispose,
  };
}
