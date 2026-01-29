<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';

interface Props {
  autoRotate?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  autoRotate: true,
});

const emit = defineEmits<{
  interact: [];
}>();

const canvasRef = ref<HTMLCanvasElement | undefined>(undefined);
const containerRef = ref<HTMLDivElement | undefined>(undefined);
const showHint = ref(true);

let scene: THREE.Scene;
let camera: THREE.PerspectiveCamera;
let renderer: THREE.WebGLRenderer;
let controls: OrbitControls;
let animationId: number | null = null;
let hasInteracted = false;
let dataOverlays: THREE.Group[] = [];
let time = 0;

// Color palette from logo
const colors = {
  primary: 0x0077B6,
  secondary: 0x00B4D8,
  accent: 0x023E8A,
  light: 0xCAF0F8,
  ground: 0xE8F4F8,
  white: 0xFFFFFF,
};

function initScene(): void {
  if (!canvasRef.value || !containerRef.value) return;

  const width = containerRef.value.clientWidth;
  const height = containerRef.value.clientHeight;

  // Scene with light gradient background
  scene = new THREE.Scene();
  scene.background = new THREE.Color(0xF0F7FA);
  scene.fog = new THREE.Fog(0xF0F7FA, 150, 400);

  // Camera - perspective for depth
  camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 1000);
  camera.position.set(120, 80, 120);
  camera.lookAt(0, 0, 0);

  // Renderer with better quality
  renderer = new THREE.WebGLRenderer({
    canvas: canvasRef.value,
    antialias: true,
    alpha: true,
  });
  renderer.setSize(width, height);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.2;

  // Lighting - soft and professional
  const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
  scene.add(ambientLight);

  const mainLight = new THREE.DirectionalLight(0xffffff, 1.2);
  mainLight.position.set(80, 120, 60);
  mainLight.castShadow = true;
  mainLight.shadow.mapSize.width = 2048;
  mainLight.shadow.mapSize.height = 2048;
  mainLight.shadow.camera.near = 10;
  mainLight.shadow.camera.far = 400;
  mainLight.shadow.camera.left = -100;
  mainLight.shadow.camera.right = 100;
  mainLight.shadow.camera.top = 100;
  mainLight.shadow.camera.bottom = -100;
  mainLight.shadow.bias = -0.0001;
  scene.add(mainLight);

  // Fill light
  const fillLight = new THREE.DirectionalLight(0x00B4D8, 0.3);
  fillLight.position.set(-50, 30, -50);
  scene.add(fillLight);

  // Hemisphere light for natural feel
  const hemiLight = new THREE.HemisphereLight(0xffffff, 0xE8F4F8, 0.6);
  scene.add(hemiLight);

  // Ground plane with subtle grid
  createGround();

  // Create terminal yard
  createTerminalYard();

  // Create AI data overlays
  createDataOverlays();

  // Controls
  controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.05;
  controls.maxPolarAngle = Math.PI / 2.2;
  controls.minPolarAngle = 0.3;
  controls.minDistance = 60;
  controls.maxDistance = 200;
  controls.enablePan = true;
  controls.panSpeed = 0.8;
  controls.rotateSpeed = 0.5;
  controls.autoRotate = props.autoRotate;
  controls.autoRotateSpeed = 0.4;
  controls.target.set(0, 0, 0);

  // Event listeners
  renderer.domElement.addEventListener('pointerdown', handleInteraction);
  renderer.domElement.addEventListener('wheel', handleInteraction);

  animate();
}

function createGround(): void {
  // Main ground
  const groundGeometry = new THREE.PlaneGeometry(500, 500);
  const groundMaterial = new THREE.MeshStandardMaterial({
    color: colors.ground,
    roughness: 0.9,
    metalness: 0.1,
  });
  const ground = new THREE.Mesh(groundGeometry, groundMaterial);
  ground.rotation.x = -Math.PI / 2;
  ground.position.y = -0.1;
  ground.receiveShadow = true;
  scene.add(ground);

  // Grid helper - subtle
  const gridHelper = new THREE.GridHelper(200, 40, 0xCCE5ED, 0xDDEEF4);
  gridHelper.position.y = 0.01;
  scene.add(gridHelper);

  // Terminal boundary outline
  const boundaryGeometry = new THREE.PlaneGeometry(140, 80);
  const boundaryMaterial = new THREE.MeshStandardMaterial({
    color: 0xFFFFFF,
    roughness: 0.5,
    metalness: 0.1,
  });
  const boundary = new THREE.Mesh(boundaryGeometry, boundaryMaterial);
  boundary.rotation.x = -Math.PI / 2;
  boundary.position.y = 0.02;
  boundary.receiveShadow = true;
  scene.add(boundary);

  // Zone markings
  createZoneMarkings();
}

function createZoneMarkings(): void {
  // Zone A marking
  const zoneAGeometry = new THREE.PlaneGeometry(60, 35);
  const zoneAMaterial = new THREE.MeshStandardMaterial({
    color: 0x0077B6,
    transparent: true,
    opacity: 0.08,
    roughness: 1,
  });
  const zoneA = new THREE.Mesh(zoneAGeometry, zoneAMaterial);
  zoneA.rotation.x = -Math.PI / 2;
  zoneA.position.set(-30, 0.03, -10);
  scene.add(zoneA);

  // Zone B marking
  const zoneBGeometry = new THREE.PlaneGeometry(60, 35);
  const zoneBMaterial = new THREE.MeshStandardMaterial({
    color: 0x00B4D8,
    transparent: true,
    opacity: 0.08,
    roughness: 1,
  });
  const zoneB = new THREE.Mesh(zoneBGeometry, zoneBMaterial);
  zoneB.rotation.x = -Math.PI / 2;
  zoneB.position.set(30, 0.03, -10);
  scene.add(zoneB);

  // Roads
  createRoads();
}

function createRoads(): void {
  const roadMaterial = new THREE.MeshStandardMaterial({
    color: 0x9CA3AF,
    roughness: 0.8,
  });

  // Main horizontal road
  const mainRoadGeometry = new THREE.PlaneGeometry(160, 8);
  const mainRoad = new THREE.Mesh(mainRoadGeometry, roadMaterial);
  mainRoad.rotation.x = -Math.PI / 2;
  mainRoad.position.set(0, 0.04, 25);
  scene.add(mainRoad);

  // Road markings
  const markingMaterial = new THREE.MeshStandardMaterial({
    color: 0xFFFFFF,
    roughness: 0.5,
  });

  for (let i = -70; i < 70; i += 10) {
    const markingGeometry = new THREE.PlaneGeometry(4, 0.3);
    const marking = new THREE.Mesh(markingGeometry, markingMaterial);
    marking.rotation.x = -Math.PI / 2;
    marking.position.set(i, 0.05, 25);
    scene.add(marking);
  }
}

function createTerminalYard(): void {
  // Container colors - corporate blue palette
  const containerColors = [
    colors.primary,    // Deep Blue
    colors.secondary,  // Light Cyan
    colors.accent,     // Navy
    0x48CAE4,          // Sky Blue
    0x90E0EF,          // Light Blue
    0xF97316,          // Orange accent (for variety)
  ];

  // Create container geometry with rounded edges effect
  const containerGeometry = new THREE.BoxGeometry(6, 2.6, 2.4);

  // Zone A containers
  for (let row = 0; row < 6; row++) {
    for (let col = 0; col < 8; col++) {
      if (Math.random() > 0.25) {
        const tiers = Math.floor(Math.random() * 3) + 1;
        const colorIndex = Math.floor(Math.random() * containerColors.length);

        for (let tier = 0; tier < tiers; tier++) {
          const color = containerColors[colorIndex] ?? colors.primary;
          createContainer(
            containerGeometry,
            color,
            -55 + col * 7,
            tier * 2.8 + 1.3,
            -25 + row * 6
          );
        }
      }
    }
  }

  // Zone B containers
  for (let row = 0; row < 6; row++) {
    for (let col = 0; col < 8; col++) {
      if (Math.random() > 0.3) {
        const tiers = Math.floor(Math.random() * 2) + 1;
        const colorIndex = Math.floor(Math.random() * containerColors.length);

        for (let tier = 0; tier < tiers; tier++) {
          const color = containerColors[colorIndex] ?? colors.primary;
          createContainer(
            containerGeometry,
            color,
            5 + col * 7,
            tier * 2.8 + 1.3,
            -25 + row * 6
          );
        }
      }
    }
  }

  // Create trucks
  createTrucks();

  // Create buildings
  createBuildings();

  // Create cranes
  createCranes();
}

function createContainer(
  geometry: THREE.BoxGeometry,
  color: number,
  x: number,
  y: number,
  z: number
): void {
  const material = new THREE.MeshStandardMaterial({
    color,
    roughness: 0.4,
    metalness: 0.3,
  });

  const container = new THREE.Mesh(geometry, material);
  container.position.set(x, y, z);
  container.castShadow = true;
  container.receiveShadow = true;

  // Add ribbing detail
  const ribGeometry = new THREE.BoxGeometry(0.1, 2.4, 2.35);
  const ribMaterial = new THREE.MeshStandardMaterial({
    color: color,
    roughness: 0.3,
    metalness: 0.4,
  });

  for (let i = -2.5; i <= 2.5; i += 0.5) {
    const rib = new THREE.Mesh(ribGeometry, ribMaterial);
    rib.position.set(i, 0, 0);
    container.add(rib);
  }

  // Add white strip (container number area)
  const stripGeometry = new THREE.BoxGeometry(2, 0.8, 0.05);
  const stripMaterial = new THREE.MeshStandardMaterial({
    color: 0xFFFFFF,
    roughness: 0.3,
  });
  const strip = new THREE.Mesh(stripGeometry, stripMaterial);
  strip.position.set(0, 0.5, 1.21);
  container.add(strip);

  scene.add(container);
}

function createTrucks(): void {
  const truckPositions = [
    { x: -70, z: 25, rotation: 0 },
    { x: -55, z: 25, rotation: 0 },
    { x: 50, z: 25, rotation: Math.PI },
    { x: 65, z: 25, rotation: Math.PI },
  ];

  truckPositions.forEach((pos) => {
    createTruck(pos.x, pos.z, pos.rotation);
  });
}

function createTruck(x: number, z: number, rotation: number): void {
  const truckGroup = new THREE.Group();

  // Cab
  const cabGeometry = new THREE.BoxGeometry(3, 2.5, 2.5);
  const cabMaterial = new THREE.MeshStandardMaterial({
    color: 0x374151,
    roughness: 0.5,
    metalness: 0.4,
  });
  const cab = new THREE.Mesh(cabGeometry, cabMaterial);
  cab.position.set(-2, 1.25, 0);
  cab.castShadow = true;
  truckGroup.add(cab);

  // Trailer
  const trailerGeometry = new THREE.BoxGeometry(8, 2.8, 2.5);
  const trailerMaterial = new THREE.MeshStandardMaterial({
    color: 0xF97316,
    roughness: 0.4,
    metalness: 0.3,
  });
  const trailer = new THREE.Mesh(trailerGeometry, trailerMaterial);
  trailer.position.set(3, 1.4, 0);
  trailer.castShadow = true;
  truckGroup.add(trailer);

  // Wheels
  const wheelGeometry = new THREE.CylinderGeometry(0.5, 0.5, 0.4, 16);
  const wheelMaterial = new THREE.MeshStandardMaterial({
    color: 0x1F2937,
    roughness: 0.8,
  });

  const wheelPositions = [
    { x: -2.5, z: 1.3 },
    { x: -2.5, z: -1.3 },
    { x: 1, z: 1.3 },
    { x: 1, z: -1.3 },
    { x: 5, z: 1.3 },
    { x: 5, z: -1.3 },
  ];

  wheelPositions.forEach((pos) => {
    const wheel = new THREE.Mesh(wheelGeometry, wheelMaterial);
    wheel.rotation.x = Math.PI / 2;
    wheel.position.set(pos.x, 0.5, pos.z);
    truckGroup.add(wheel);
  });

  truckGroup.position.set(x, 0, z);
  truckGroup.rotation.y = rotation;
  scene.add(truckGroup);
}

function createBuildings(): void {
  // Main office building
  const buildingGeometry = new THREE.BoxGeometry(20, 12, 15);
  const buildingMaterial = new THREE.MeshStandardMaterial({
    color: 0xE5E7EB,
    roughness: 0.6,
    metalness: 0.2,
  });
  const building = new THREE.Mesh(buildingGeometry, buildingMaterial);
  building.position.set(80, 6, -20);
  building.castShadow = true;
  building.receiveShadow = true;
  scene.add(building);

  // Windows
  const windowMaterial = new THREE.MeshStandardMaterial({
    color: 0x0077B6,
    roughness: 0.1,
    metalness: 0.8,
    transparent: true,
    opacity: 0.7,
  });

  for (let floor = 0; floor < 3; floor++) {
    for (let w = 0; w < 4; w++) {
      const windowGeometry = new THREE.PlaneGeometry(3, 2);
      const windowMesh = new THREE.Mesh(windowGeometry, windowMaterial);
      windowMesh.position.set(80 - 10.01, 3 + floor * 3.5, -27 + w * 5);
      windowMesh.rotation.y = Math.PI / 2;
      scene.add(windowMesh);
    }
  }

  // Gate structure
  const gateGeometry = new THREE.BoxGeometry(4, 6, 12);
  const gateMaterial = new THREE.MeshStandardMaterial({
    color: colors.primary,
    roughness: 0.5,
    metalness: 0.3,
  });
  const gate = new THREE.Mesh(gateGeometry, gateMaterial);
  gate.position.set(-80, 3, 25);
  gate.castShadow = true;
  scene.add(gate);

  // Gate sign
  const signGeometry = new THREE.BoxGeometry(8, 2, 0.3);
  const signMaterial = new THREE.MeshStandardMaterial({
    color: 0xFFFFFF,
    roughness: 0.3,
  });
  const sign = new THREE.Mesh(signGeometry, signMaterial);
  sign.position.set(-80, 7, 25);
  scene.add(sign);
}

function createCranes(): void {
  // RTG Crane
  createRTGCrane(-30, 10);
  createRTGCrane(30, 10);
}

function createRTGCrane(x: number, z: number): void {
  const craneGroup = new THREE.Group();

  // Vertical supports
  const supportGeometry = new THREE.BoxGeometry(1, 20, 1);
  const supportMaterial = new THREE.MeshStandardMaterial({
    color: colors.primary,
    roughness: 0.4,
    metalness: 0.5,
  });

  const support1 = new THREE.Mesh(supportGeometry, supportMaterial);
  support1.position.set(-10, 10, 0);
  support1.castShadow = true;
  craneGroup.add(support1);

  const support2 = new THREE.Mesh(supportGeometry, supportMaterial);
  support2.position.set(10, 10, 0);
  support2.castShadow = true;
  craneGroup.add(support2);

  // Horizontal beam
  const beamGeometry = new THREE.BoxGeometry(22, 2, 1.5);
  const beam = new THREE.Mesh(beamGeometry, supportMaterial);
  beam.position.set(0, 20, 0);
  beam.castShadow = true;
  craneGroup.add(beam);

  // Trolley
  const trolleyGeometry = new THREE.BoxGeometry(3, 1.5, 2);
  const trolleyMaterial = new THREE.MeshStandardMaterial({
    color: colors.secondary,
    roughness: 0.3,
    metalness: 0.6,
  });
  const trolley = new THREE.Mesh(trolleyGeometry, trolleyMaterial);
  trolley.position.set(0, 18.5, 0);
  craneGroup.add(trolley);

  craneGroup.position.set(x, 0, z);
  scene.add(craneGroup);
}

function createDataOverlays(): void {
  // Create floating data panels showing AI tracking
  const overlayPositions = [
    { x: -40, y: 15, z: -15, label: 'MSKU7234561', status: 'LADEN' },
    { x: -20, y: 12, z: -5, label: 'HDMU8845673', status: 'EMPTY' },
    { x: 20, y: 14, z: -20, label: 'TCLU9912345', status: 'LADEN' },
    { x: 40, y: 11, z: -10, label: 'BMOU4456789', status: 'EXPORT' },
  ];

  overlayPositions.forEach((pos, index) => {
    const overlay = createDataPanel(pos.label, pos.status, index);
    overlay.position.set(pos.x, pos.y, pos.z);
    dataOverlays.push(overlay);
    scene.add(overlay);
  });

  // Add connection lines
  createConnectionLines();
}

function createDataPanel(_label: string, status: string, index: number): THREE.Group {
  const group = new THREE.Group();

  // Panel background
  const panelGeometry = new THREE.PlaneGeometry(8, 3);
  const panelMaterial = new THREE.MeshBasicMaterial({
    color: 0xFFFFFF,
    transparent: true,
    opacity: 0.9,
    side: THREE.DoubleSide,
  });
  const panel = new THREE.Mesh(panelGeometry, panelMaterial);
  group.add(panel);

  // Border
  const borderGeometry = new THREE.EdgesGeometry(panelGeometry);
  const borderMaterial = new THREE.LineBasicMaterial({
    color: colors.primary,
    linewidth: 2,
  });
  const border = new THREE.LineSegments(borderGeometry, borderMaterial);
  group.add(border);

  // Status indicator dot
  const dotGeometry = new THREE.CircleGeometry(0.3, 16);
  const dotMaterial = new THREE.MeshBasicMaterial({
    color: status === 'LADEN' ? 0x22C55E : status === 'EMPTY' ? 0xF97316 : 0x0077B6,
    side: THREE.DoubleSide,
  });
  const dot = new THREE.Mesh(dotGeometry, dotMaterial);
  dot.position.set(-3, 0.8, 0.01);
  group.add(dot);

  // Make panel face camera (billboard effect handled in animate)
  group.userData = { index };

  return group;
}

function createConnectionLines(): void {
  const lineMaterial = new THREE.LineDashedMaterial({
    color: colors.secondary,
    dashSize: 1,
    gapSize: 0.5,
    transparent: true,
    opacity: 0.5,
  });

  dataOverlays.forEach((overlay) => {
    const points = [
      overlay.position.clone(),
      new THREE.Vector3(overlay.position.x, 0, overlay.position.z),
    ];
    const geometry = new THREE.BufferGeometry().setFromPoints(points);
    const line = new THREE.Line(geometry, lineMaterial);
    line.computeLineDistances();
    scene.add(line);
  });
}

function handleInteraction(): void {
  if (!hasInteracted) {
    hasInteracted = true;
    showHint.value = false;
    emit('interact');
  }
}

function animate(): void {
  animationId = requestAnimationFrame(animate);
  time += 0.01;

  // Animate data overlays (floating effect)
  dataOverlays.forEach((overlay, index) => {
    overlay.position.y += Math.sin(time + index) * 0.01;
    // Billboard effect - face camera
    overlay.lookAt(camera.position);
  });

  controls.update();
  renderer.render(scene, camera);
}

function handleResize(): void {
  if (!canvasRef.value || !containerRef.value || !camera || !renderer) return;

  const width = containerRef.value.clientWidth;
  const height = containerRef.value.clientHeight;

  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  renderer.setSize(width, height);
}

onMounted(() => {
  initScene();
  window.addEventListener('resize', handleResize);

  setTimeout(() => {
    if (!hasInteracted) {
      showHint.value = false;
    }
  }, 6000);
});

onUnmounted(() => {
  if (animationId) {
    cancelAnimationFrame(animationId);
  }
  if (renderer) {
    renderer.dispose();
    renderer.domElement.removeEventListener('pointerdown', handleInteraction);
    renderer.domElement.removeEventListener('wheel', handleInteraction);
  }
  window.removeEventListener('resize', handleResize);
});
</script>

<template>
  <div ref="containerRef" class="hero-3d-container">
    <canvas ref="canvasRef" class="hero-canvas" />

    <Transition name="fade">
      <div v-if="showHint" class="interaction-hint">
        <div class="hint-icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            <path d="M9 12l2 2 4-4" />
          </svg>
        </div>
        <span>Перетащите для просмотра</span>
      </div>
    </Transition>

    <div class="hero-overlay">
      <div class="hero-badge">
        <span class="badge-dot"></span>
        AI-мониторинг в реальном времени
      </div>
    </div>

    <!-- Data metrics floating -->
    <div class="floating-metrics">
      <div class="metric">
        <span class="metric-value">156</span>
        <span class="metric-label">Контейнеров онлайн</span>
      </div>
      <div class="metric">
        <span class="metric-value">12</span>
        <span class="metric-label">Активных ТС</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=DM+Sans:wght@400;500;600&display=swap');

.hero-3d-container {
  position: relative;
  width: 100%;
  height: 100vh;
  overflow: hidden;
  background: linear-gradient(180deg, #F0F7FA 0%, #E8F4F8 100%);
}

.hero-canvas {
  width: 100%;
  height: 100%;
  display: block;
  cursor: grab;
}

.hero-canvas:active {
  cursor: grabbing;
}

.interaction-hint {
  position: absolute;
  bottom: 100px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 24px;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(0, 119, 182, 0.2);
  border-radius: 50px;
  color: #0077B6;
  font-family: 'DM Sans', sans-serif;
  font-size: 14px;
  font-weight: 500;
  box-shadow: 0 8px 32px rgba(0, 119, 182, 0.15);
  z-index: 10;
  animation: float 3s ease-in-out infinite;
}

.hint-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

@keyframes float {
  0%, 100% {
    transform: translateX(-50%) translateY(0);
  }
  50% {
    transform: translateX(-50%) translateY(-8px);
  }
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.5s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

.hero-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  pointer-events: none;
}

.hero-badge {
  position: absolute;
  top: 24px;
  right: 24px;
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 20px;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(0, 119, 182, 0.15);
  border-radius: 50px;
  color: #0077B6;
  font-family: 'DM Sans', sans-serif;
  font-size: 13px;
  font-weight: 600;
  box-shadow: 0 4px 20px rgba(0, 119, 182, 0.1);
}

.badge-dot {
  width: 8px;
  height: 8px;
  background: #22C55E;
  border-radius: 50%;
  animation: pulse-dot 2s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.6;
    transform: scale(1.2);
  }
}

.floating-metrics {
  position: absolute;
  bottom: 24px;
  right: 24px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  pointer-events: none;
}

.metric {
  display: flex;
  flex-direction: column;
  padding: 16px 20px;
  background: rgba(255, 255, 255, 0.95);
  border: 1px solid rgba(0, 119, 182, 0.1);
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 119, 182, 0.08);
}

.metric-value {
  font-family: 'Plus Jakarta Sans', sans-serif;
  font-size: 28px;
  font-weight: 700;
  color: #0077B6;
  line-height: 1;
}

.metric-label {
  font-family: 'DM Sans', sans-serif;
  font-size: 12px;
  font-weight: 500;
  color: #64748B;
  margin-top: 4px;
}

@media (max-width: 768px) {
  .hero-badge {
    top: 16px;
    right: 16px;
    font-size: 11px;
    padding: 8px 14px;
  }

  .floating-metrics {
    bottom: 16px;
    right: 16px;
  }

  .metric {
    padding: 12px 16px;
  }

  .metric-value {
    font-size: 22px;
  }

  .interaction-hint {
    bottom: 80px;
    font-size: 12px;
    padding: 10px 18px;
  }
}
</style>
