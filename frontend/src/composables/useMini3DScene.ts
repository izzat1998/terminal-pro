/**
 * Simplified Three.js scene for focused position viewer (modal)
 * Shows a 5×5 grid area around a target position with basic controls
 */

import { ref, shallowRef, onUnmounted, type Ref } from 'vue';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { ZONE_LAYOUT, SPACING } from '../types/placement';
import type { ZoneCode } from '../types/placement';

// Parsed coordinate for positioning
export interface ParsedCoordinate {
  zone: ZoneCode;
  row: number;
  bay: number;
  tier: number;
  subSlot: 'A' | 'B';
}

// Parse coordinate string like "A-R03-B05-T2-A"
export function parseCoordinate(coordinate: string): ParsedCoordinate | null {
  const match = coordinate.match(/^([A-E])-R(\d{2})-B(\d{2})-T(\d)-([AB])$/);
  if (!match) return null;

  return {
    zone: match[1] as ZoneCode,
    row: parseInt(match[2] ?? '0', 10),
    bay: parseInt(match[3] ?? '0', 10),
    tier: parseInt(match[4] ?? '0', 10),
    subSlot: match[5] as 'A' | 'B',
  };
}

export function useMini3DScene(canvasRef: Ref<HTMLCanvasElement | undefined>) {
  const scene = shallowRef<THREE.Scene>();
  const camera = shallowRef<THREE.OrthographicCamera>();
  const renderer = shallowRef<THREE.WebGLRenderer>();
  const controls = shallowRef<OrbitControls>();
  const isInitialized = ref(false);
  let animationId: number | null = null;

  // Target position for centering the view
  const targetCenter = new THREE.Vector3();

  /**
   * Initialize the mini 3D scene centered on a specific coordinate
   */
  function initScene(coordinate: string): boolean {
    if (!canvasRef.value || isInitialized.value) return false;

    const parsed = parseCoordinate(coordinate);
    if (!parsed) return false;

    const zoneLayout = ZONE_LAYOUT[parsed.zone];
    if (!zoneLayout) return false;

    // Calculate world position of target
    const targetX = zoneLayout.xOffset + (parsed.bay - 1) * SPACING.bay + SPACING.bay / 2;
    const targetZ = zoneLayout.zOffset + (parsed.row - 1) * SPACING.row + SPACING.row / 2;
    targetCenter.set(targetX, 0, targetZ);

    // Scene with light background
    scene.value = new THREE.Scene();
    scene.value.background = new THREE.Color(0xf0f0f0);

    // Camera (orthographic) - smaller frustum for focused view
    const aspect = canvasRef.value.clientWidth / canvasRef.value.clientHeight;
    const frustumSize = 40; // Smaller than full view (90)
    camera.value = new THREE.OrthographicCamera(
      -frustumSize * aspect / 2,
      frustumSize * aspect / 2,
      frustumSize / 2,
      -frustumSize / 2,
      0.1,
      300
    );
    // Position camera for isometric view looking at target
    camera.value.position.set(targetX + 25, 35, targetZ + 25);
    camera.value.lookAt(targetCenter);
    camera.value.zoom = 1.8;
    camera.value.updateProjectionMatrix();

    // Renderer
    renderer.value = new THREE.WebGLRenderer({
      canvas: canvasRef.value,
      antialias: true,
    });
    renderer.value.setSize(canvasRef.value.clientWidth, canvasRef.value.clientHeight);
    renderer.value.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.value.shadowMap.enabled = true;
    renderer.value.shadowMap.type = THREE.PCFSoftShadowMap;

    // Controls - basic orbit
    controls.value = new OrbitControls(camera.value, renderer.value.domElement);
    controls.value.enableDamping = true;
    controls.value.dampingFactor = 0.1;
    controls.value.maxPolarAngle = Math.PI / 2.1;
    controls.value.minPolarAngle = 0;
    controls.value.enablePan = true;
    controls.value.panSpeed = 1.0;
    controls.value.screenSpacePanning = true;
    controls.value.enableRotate = true;
    controls.value.rotateSpeed = 0.8;
    controls.value.minZoom = 0.5;
    controls.value.maxZoom = 4.0;
    controls.value.target.copy(targetCenter);

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
    scene.value.add(ambientLight);

    const directionalLight = new THREE.DirectionalLight(0xffffff, 1.0);
    directionalLight.position.set(targetX + 30, 50, targetZ + 20);
    directionalLight.castShadow = true;
    directionalLight.shadow.mapSize.width = 1024;
    directionalLight.shadow.mapSize.height = 1024;
    directionalLight.shadow.camera.near = 10;
    directionalLight.shadow.camera.far = 150;
    directionalLight.shadow.camera.left = -40;
    directionalLight.shadow.camera.right = 40;
    directionalLight.shadow.camera.top = 40;
    directionalLight.shadow.camera.bottom = -40;
    directionalLight.shadow.bias = -0.001;
    scene.value.add(directionalLight);

    // Ground plane (small, centered on target)
    const groundGeometry = new THREE.PlaneGeometry(150, 150);
    const groundMaterial = new THREE.MeshStandardMaterial({
      color: 0xd4d4d4,
      roughness: 0.95,
      metalness: 0.0,
    });
    const ground = new THREE.Mesh(groundGeometry, groundMaterial);
    ground.rotation.x = -Math.PI / 2;
    ground.position.set(targetX, -0.05, targetZ);
    ground.receiveShadow = true;
    scene.value.add(ground);

    // Add focused zone marking (5×5 area)
    createFocusedGridMarkings(parsed, zoneLayout.xOffset, zoneLayout.zOffset);

    isInitialized.value = true;
    animate();
    return true;
  }

  /**
   * Create grid markings for the visible area (±2 rows/bays)
   */
  function createFocusedGridMarkings(
    parsed: ParsedCoordinate,
    zoneXOffset: number,
    zoneZOffset: number
  ): void {
    if (!scene.value) return;

    // Calculate visible range (±2, clamped to 1-10)
    const minRow = Math.max(1, parsed.row - 2);
    const maxRow = Math.min(10, parsed.row + 2);
    const minBay = Math.max(1, parsed.bay - 2);
    const maxBay = Math.min(10, parsed.bay + 2);

    // Zone floor marking for visible area
    const startX = zoneXOffset + (minBay - 1) * SPACING.bay;
    const endX = zoneXOffset + maxBay * SPACING.bay;
    const startZ = zoneZOffset + (minRow - 1) * SPACING.row;
    const endZ = zoneZOffset + maxRow * SPACING.row;
    const width = endX - startX;
    const depth = endZ - startZ;

    const zoneGeometry = new THREE.PlaneGeometry(width, depth);
    const zoneMaterial = new THREE.MeshStandardMaterial({
      color: 0xcce5ff,
      roughness: 0.9,
      metalness: 0,
      transparent: true,
      opacity: 0.5,
    });
    const zonePlane = new THREE.Mesh(zoneGeometry, zoneMaterial);
    zonePlane.rotation.x = -Math.PI / 2;
    zonePlane.position.set(startX + width / 2, 0.01, startZ + depth / 2);
    zonePlane.receiveShadow = true;
    scene.value.add(zonePlane);

    // Grid lines
    const lineMaterial = new THREE.LineBasicMaterial({
      color: 0x999999,
      transparent: true,
      opacity: 0.5,
    });

    // Vertical lines (bays)
    for (let bay = minBay; bay <= maxBay + 1; bay++) {
      const x = zoneXOffset + (bay - 1) * SPACING.bay;
      const points = [
        new THREE.Vector3(x, 0.02, startZ),
        new THREE.Vector3(x, 0.02, endZ),
      ];
      const geometry = new THREE.BufferGeometry().setFromPoints(points);
      const line = new THREE.Line(geometry, lineMaterial);
      scene.value.add(line);
    }

    // Horizontal lines (rows)
    for (let row = minRow; row <= maxRow + 1; row++) {
      const z = zoneZOffset + (row - 1) * SPACING.row;
      const points = [
        new THREE.Vector3(startX, 0.02, z),
        new THREE.Vector3(endX, 0.02, z),
      ];
      const geometry = new THREE.BufferGeometry().setFromPoints(points);
      const line = new THREE.Line(geometry, lineMaterial);
      scene.value.add(line);
    }

    // Add row/bay labels
    addGridLabels(parsed, zoneXOffset, zoneZOffset, minRow, maxRow, minBay, maxBay);
  }

  /**
   * Add row and bay labels to the ground
   */
  function addGridLabels(
    _parsed: ParsedCoordinate,
    zoneXOffset: number,
    zoneZOffset: number,
    minRow: number,
    maxRow: number,
    minBay: number,
    maxBay: number
  ): void {
    if (!scene.value) return;

    // Row labels (left side)
    for (let row = minRow; row <= maxRow; row++) {
      const z = zoneZOffset + (row - 1) * SPACING.row + SPACING.row / 2;
      const x = zoneXOffset + (minBay - 1) * SPACING.bay - 4;
      addGroundLabel(`R${row}`, x, z, '#c0392b', true);
    }

    // Bay labels (front)
    for (let bay = minBay; bay <= maxBay; bay++) {
      const x = zoneXOffset + (bay - 1) * SPACING.bay + SPACING.bay / 2;
      const z = zoneZOffset + (minRow - 1) * SPACING.row - 3;
      addGroundLabel(`B${bay}`, x, z, '#2980b9', false);
    }
  }

  /**
   * Add a label painted on the ground
   */
  function addGroundLabel(
    text: string,
    x: number,
    z: number,
    color: string,
    isRow: boolean
  ): void {
    if (!scene.value) return;

    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d');
    if (!context) return;

    canvas.width = 96;
    canvas.height = 48;

    context.fillStyle = 'rgba(255, 255, 255, 0.9)';
    context.fillRect(0, 0, 96, 48);

    context.strokeStyle = color;
    context.lineWidth = 3;
    context.strokeRect(2, 2, 92, 44);

    context.fillStyle = color;
    context.font = 'bold 28px Arial';
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.fillText(text, 48, 24);

    const texture = new THREE.CanvasTexture(canvas);

    const geometry = new THREE.PlaneGeometry(4, 2);
    const material = new THREE.MeshBasicMaterial({
      map: texture,
      transparent: true,
      side: THREE.DoubleSide,
      depthWrite: false,
    });

    const mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(x, 0.05, z);
    mesh.rotation.x = -Math.PI / 2;

    if (isRow) {
      mesh.rotation.z = Math.PI / 2;
    }

    scene.value.add(mesh);
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
    const frustumSize = 40;

    camera.value.left = -frustumSize * aspect / 2;
    camera.value.right = frustumSize * aspect / 2;
    camera.value.top = frustumSize / 2;
    camera.value.bottom = -frustumSize / 2;
    camera.value.updateProjectionMatrix();

    renderer.value.setSize(width, height);
  }

  function resetCamera(): void {
    if (!camera.value || !controls.value) return;

    camera.value.position.set(
      targetCenter.x + 25,
      35,
      targetCenter.z + 25
    );
    camera.value.zoom = 1.8;
    camera.value.lookAt(targetCenter);
    camera.value.updateProjectionMatrix();
    controls.value.target.copy(targetCenter);
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
    targetCenter,
    initScene,
    handleResize,
    resetCamera,
    dispose,
    parseCoordinate,
  };
}
