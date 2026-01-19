/**
 * Container mesh rendering composable using InstancedMesh for performance
 * Supports: 20ft/40ft sizes, Standard/High Cube heights, Laden/Empty status
 * Total: 8 mesh combinations for accurate visual representation
 */

import { shallowRef, type Ref } from 'vue';
import * as THREE from 'three';
import type { ContainerPlacement, Position, ZoneCode, ColorMode, PositionMarkerData, SuggestionResponse } from '../types/placement';
import {
  CONTAINER_COLORS,
  ZONE_LAYOUT,
  SPACING,
  CONTAINER_DIMENSIONS,
  MARKER_COLORS,
  getContainerSize,
  isHighCube,
  getDwellTimeColor,
  getContainerColor,
  getContainerEdgeColor,
} from '../types/placement';

// Mesh key type for all combinations
type MeshKey = 'laden20' | 'laden20HC' | 'laden40' | 'laden40HC' |
               'empty20' | 'empty20HC' | 'empty40' | 'empty40HC';

interface ContainerMeshInfo {
  meshKey: MeshKey;
  instanceId: number;
  isLaden: boolean;
  size: '20ft' | '40ft' | '45ft';
}

export function useContainerMesh(scene: Ref<THREE.Scene | undefined>) {
  const meshes = shallowRef<Record<MeshKey, THREE.InstancedMesh> | null>(null);
  const containerMap = new Map<number, ContainerMeshInfo>();
  const containerById = new Map<number, ContainerPlacement>(); // Quick lookup by id
  const labelSprites: THREE.Sprite[] = [];
  const wallTextMeshes: THREE.Mesh[] = []; // Text on container walls
  const edgeLines: THREE.LineSegments[] = []; // Dark outlines for each container
  const showLabels = shallowRef(true);
  const showWallText = shallowRef(true);
  const colorMode = shallowRef<ColorMode>('status'); // 'status' or 'dwell_time'
  const filteredCompanyName = shallowRef<string | null>(null); // Company filter for dimming

  // Placement mode visual state - used to dim containers and hide labels during placement
  let placementModeActive = false;
  let preplacementLabelsState = true;
  let preplacementWallTextState = true;

  // Pending container tracking (solid orange color, no animation)
  const pendingContainerIds = new Set<number>();
  let pendingAnimationId: number | null = null; // Kept for cleanup compatibility

  // Track counts for each mesh type
  const counts: Record<MeshKey, number> = {
    laden20: 0, laden20HC: 0, laden40: 0, laden40HC: 0,
    empty20: 0, empty20HC: 0, empty40: 0, empty40HC: 0,
  };

  // Raycaster for click detection
  const raycaster = new THREE.Raycaster();
  const mouse = new THREE.Vector2();

  // Helper to safely get zone layout (throws if zone not found)
  function getZoneLayout(zone: ZoneCode) {
    const layout = ZONE_LAYOUT[zone];
    if (!layout) {
      throw new Error(`Zone ${zone} not configured in ZONE_LAYOUT`);
    }
    return layout;
  }

  function initMeshes(maxContainers: number = 2500): void {
    if (!scene.value) return;

    // Create geometries for all size/height combinations
    const geometries = {
      '20': new THREE.BoxGeometry(
        CONTAINER_DIMENSIONS['20ft'].length,
        CONTAINER_DIMENSIONS['20ft'].height,
        CONTAINER_DIMENSIONS['20ft'].width
      ),
      '20HC': new THREE.BoxGeometry(
        CONTAINER_DIMENSIONS['20ft_HC'].length,
        CONTAINER_DIMENSIONS['20ft_HC'].height,
        CONTAINER_DIMENSIONS['20ft_HC'].width
      ),
      '40': new THREE.BoxGeometry(
        CONTAINER_DIMENSIONS['40ft'].length,
        CONTAINER_DIMENSIONS['40ft'].height,
        CONTAINER_DIMENSIONS['40ft'].width
      ),
      '40HC': new THREE.BoxGeometry(
        CONTAINER_DIMENSIONS['40ft_HC'].length,
        CONTAINER_DIMENSIONS['40ft_HC'].height,
        CONTAINER_DIMENSIONS['40ft_HC'].width
      ),
    };

    // Materials - use WHITE base color so instance colors display correctly
    // (Three.js InstancedMesh multiplies instance color × material color)
    // Actual colors are set via setColorAt() in applyColorMode()
    const whiteMaterial = new THREE.MeshLambertMaterial({ color: 0xffffff });

    // Create all 8 mesh combinations (4 size/status combos × 2 height variants)
    const createMesh = (
      geometry: THREE.BoxGeometry,
      material: THREE.MeshLambertMaterial,
      name: string
    ): THREE.InstancedMesh => {
      const mesh = new THREE.InstancedMesh(geometry, material.clone(), maxContainers);
      mesh.count = 0;
      mesh.name = name;
      mesh.castShadow = true;
      mesh.receiveShadow = true;
      // Disable frustum culling to prevent containers disappearing during zoom
      // (InstancedMesh bounding box doesn't auto-update with instance positions)
      mesh.frustumCulled = false;
      return mesh;
    };

    meshes.value = {
      // All meshes use white material - colors are set via instanceColor
      laden20: createMesh(geometries['20'], whiteMaterial, 'laden20ft'),
      laden20HC: createMesh(geometries['20HC'], whiteMaterial, 'laden20ftHC'),
      empty20: createMesh(geometries['20'], whiteMaterial, 'empty20ft'),
      empty20HC: createMesh(geometries['20HC'], whiteMaterial, 'empty20ftHC'),
      laden40: createMesh(geometries['40'], whiteMaterial, 'laden40ft'),
      laden40HC: createMesh(geometries['40HC'], whiteMaterial, 'laden40ftHC'),
      empty40: createMesh(geometries['40'], whiteMaterial, 'empty40ft'),
      empty40HC: createMesh(geometries['40HC'], whiteMaterial, 'empty40ftHC'),
    };

    // Add all meshes to scene
    Object.values(meshes.value).forEach(mesh => scene.value!.add(mesh));
  }

  // Determine which mesh to use for a container
  function getMeshKey(isoType: string, isLaden: boolean): MeshKey {
    const size = getContainerSize(isoType);
    const hc = isHighCube(isoType);
    const is20ft = size === '20ft';

    // Build mesh key from status + size + HC variant
    // 40ft and 45ft both use 40ft geometry
    if (isLaden) {
      if (is20ft) {
        return hc ? 'laden20HC' : 'laden20';
      }
      return hc ? 'laden40HC' : 'laden40';
    }

    if (is20ft) {
      return hc ? 'empty20HC' : 'empty20';
    }
    return hc ? 'empty40HC' : 'empty40';
  }

  // Create a text sprite for container number label
  function createContainerLabel(containerNumber: string, x: number, y: number, z: number): THREE.Sprite {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d')!;

    // High-resolution canvas for crisp text
    canvas.width = 256;
    canvas.height = 64;

    // Background with rounded corners
    context.fillStyle = 'rgba(0, 0, 0, 0.75)';
    context.beginPath();
    context.roundRect(4, 4, 248, 56, 8);
    context.fill();

    // Text
    context.fillStyle = '#ffffff';
    context.font = 'bold 28px monospace';
    context.textAlign = 'center';
    context.textBaseline = 'middle';

    // Truncate to last 7 chars if too long (e.g., "6565958" from "HDMU6565958")
    const displayText = containerNumber.length > 11
      ? containerNumber.slice(-7)
      : containerNumber;
    context.fillText(displayText, 128, 32);

    const texture = new THREE.CanvasTexture(canvas);
    texture.minFilter = THREE.LinearFilter;
    texture.magFilter = THREE.LinearFilter;

    const material = new THREE.SpriteMaterial({
      map: texture,
      transparent: true,
      depthTest: false,
      depthWrite: false,
    });

    const sprite = new THREE.Sprite(material);
    sprite.position.set(x, y, z);
    sprite.scale.set(5, 1.25, 1); // Wider for container number

    return sprite;
  }

  // Clear all existing labels
  function clearLabels(): void {
    for (const sprite of labelSprites) {
      if (sprite.material.map) {
        sprite.material.map.dispose();
      }
      sprite.material.dispose();
      scene.value?.remove(sprite);
    }
    labelSprites.length = 0;
  }

  // Toggle label visibility
  function toggleLabels(visible?: boolean): void {
    showLabels.value = visible ?? !showLabels.value;
    for (const sprite of labelSprites) {
      sprite.visible = showLabels.value;
    }
  }

  // Create wall text for container side (like real shipping containers)
  function createWallText(
    containerNumber: string,
    x: number,
    y: number,
    z: number,
    containerLength: number,
    _containerHeight: number, // Kept for future use (text vertical positioning)
    containerWidth: number,
    _isLaden: boolean // Kept for future use (text color based on status)
  ): THREE.Mesh {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d')!;

    // High-resolution canvas for crisp text
    canvas.width = 512;
    canvas.height = 128;

    // Transparent background - text only
    context.clearRect(0, 0, canvas.width, canvas.height);

    // Text styling - white text with dark shadow for readability
    // Real containers use white or black text depending on container color
    context.shadowColor = 'rgba(0, 0, 0, 0.8)';
    context.shadowBlur = 4;
    context.shadowOffsetX = 2;
    context.shadowOffsetY = 2;

    context.fillStyle = '#ffffff';
    context.font = 'bold 64px monospace';
    context.textAlign = 'center';
    context.textBaseline = 'middle';

    // Full container number (e.g., "HDMU6565958")
    context.fillText(containerNumber, 256, 64);

    const texture = new THREE.CanvasTexture(canvas);
    texture.minFilter = THREE.LinearFilter;
    texture.magFilter = THREE.LinearFilter;

    // Create plane geometry sized proportionally to container
    // Text should be about 60% of container length
    const textWidth = containerLength * 0.7;
    const textHeight = textWidth * 0.25; // Maintain aspect ratio

    const geometry = new THREE.PlaneGeometry(textWidth, textHeight);
    const material = new THREE.MeshBasicMaterial({
      map: texture,
      transparent: true,
      side: THREE.DoubleSide,
      depthWrite: false,
    });

    const mesh = new THREE.Mesh(geometry, material);

    // Position on the front side of the container (positive Z direction)
    // Offset slightly to prevent z-fighting
    mesh.position.set(
      x,
      y, // Center vertically on the container
      z + containerWidth / 2 + 0.05 // Slightly in front of the container wall
    );

    // No rotation needed - PlaneGeometry faces +Z by default
    // which is the direction we want (outward from container front)

    return mesh;
  }

  // Clear all wall text meshes
  function clearWallText(): void {
    for (const mesh of wallTextMeshes) {
      if (mesh.material instanceof THREE.MeshBasicMaterial && mesh.material.map) {
        mesh.material.map.dispose();
      }
      (mesh.material as THREE.Material).dispose();
      mesh.geometry.dispose();
      scene.value?.remove(mesh);
    }
    wallTextMeshes.length = 0;
  }

  // Toggle wall text visibility
  function toggleWallText(visible?: boolean): void {
    showWallText.value = visible ?? !showWallText.value;
    for (const mesh of wallTextMeshes) {
      mesh.visible = showWallText.value;
    }
  }

  // Clear all edge lines
  function clearEdgeLines(): void {
    for (const line of edgeLines) {
      line.geometry.dispose();
      (line.material as THREE.LineBasicMaterial).dispose();
      scene.value?.remove(line);
    }
    edgeLines.length = 0;
  }

  // Create edge outline for a container with size-specific colors
  function createContainerEdges(
    length: number,
    height: number,
    width: number,
    x: number,
    y: number,
    z: number,
    isLaden: boolean,
    size: '20ft' | '40ft' | '45ft',
    isPending: boolean = false
  ): THREE.LineSegments {
    const geometry = new THREE.BoxGeometry(length, height, width);
    const edges = new THREE.EdgesGeometry(geometry);
    // Pending containers get dark orange edges, others get size-specific colors
    const edgeColor = isPending ? 0xd46b08 : getContainerEdgeColor(isLaden, size);
    const material = new THREE.LineBasicMaterial({
      color: edgeColor,
      linewidth: 2,
    });
    const lineSegments = new THREE.LineSegments(edges, material);
    lineSegments.position.set(x, y, z);
    geometry.dispose(); // Original box geometry no longer needed
    return lineSegments;
  }

  // Convert position coordinates to world (3D) coordinates
  // Used by both updateContainers() and position marker visualization
  function positionToWorld(position: Position, isoType: string = '45G1'): { x: number; y: number; z: number } {
    const zoneLayout = getZoneLayout(position.zone as ZoneCode);
    const size = getContainerSize(isoType);
    const hc = isHighCube(isoType);

    const dimKey = hc
      ? (size === '20ft' ? '20ft_HC' : '40ft_HC')
      : (size === '20ft' ? '20ft' : '40ft');
    const dimensions = CONTAINER_DIMENSIONS[dimKey as keyof typeof CONTAINER_DIMENSIONS];

    // X: Bay position based on size and sub_slot
    let x: number;
    const subSlot = position.sub_slot || 'A';

    if (size === '20ft') {
      const bayStartX = zoneLayout.xOffset + (position.bay - 1) * SPACING.bay;
      if (subSlot === 'A') {
        x = bayStartX + dimensions.length / 2 + SPACING.gap;
      } else {
        x = bayStartX + dimensions.length + SPACING.gap * 2 + dimensions.length / 2;
      }
    } else {
      x = zoneLayout.xOffset + (position.bay - 0.5) * SPACING.bay;
    }

    // Y: Tier position (vertical stacking)
    const y = (position.tier - 1) * SPACING.tier + dimensions.height / 2;

    // Z: Row position (container width direction)
    const z = zoneLayout.zOffset + (position.row - 0.5) * SPACING.row;

    return { x, y, z };
  }

  function updateContainers(containers: ContainerPlacement[]): void {
    if (!meshes.value || !scene.value) return;

    // Stop any existing pending animation and clear tracking
    stopPendingAnimation();
    pendingContainerIds.clear();

    containerMap.clear();
    containerById.clear();
    clearLabels(); // Clear existing labels
    clearWallText(); // Clear existing wall text
    clearEdgeLines(); // Clear existing edge outlines

    // Reset all counts
    (Object.keys(counts) as MeshKey[]).forEach(key => counts[key] = 0);

    const matrix = new THREE.Matrix4();

    // Build a map of positions to find top containers (for label display)
    const positionMap = new Map<string, ContainerPlacement>();
    for (const container of containers) {
      // Store in quick lookup map
      containerById.set(container.id, container);

      const pos = container.position;
      const key = `${pos.zone}-${pos.row}-${pos.bay}`;
      const existing = positionMap.get(key);
      // Keep the one with highest tier
      if (!existing || pos.tier > existing.position.tier) {
        positionMap.set(key, container);
      }
    }
    const topContainerIds = new Set([...positionMap.values()].map(c => c.id));

    for (const container of containers) {
      const pos = container.position;
      const isLaden = container.status === 'LADEN';
      const meshKey = getMeshKey(container.iso_type, isLaden);
      const size = getContainerSize(container.iso_type);
      const hc = isHighCube(container.iso_type);

      // Get the correct dimensions for this container
      const dimKey = hc
        ? (size === '20ft' ? '20ft_HC' : '40ft_HC')
        : (size === '20ft' ? '20ft' : '40ft');
      const containerHeight = CONTAINER_DIMENSIONS[dimKey].height;
      const containerLength = CONTAINER_DIMENSIONS[dimKey].length;
      const containerWidth = CONTAINER_DIMENSIONS[dimKey].width;

      // Calculate world position using shared helper
      const { x, y, z } = positionToWorld(pos, container.iso_type);

      matrix.setPosition(x, y, z);

      const mesh = meshes.value[meshKey];
      const instanceId = counts[meshKey];
      mesh.setMatrixAt(instanceId, matrix);
      containerMap.set(container.id, { meshKey, instanceId, isLaden, size });
      counts[meshKey]++;

      // Track pending containers (they get solid orange color via applyColorMode)
      const isPending = container.placement_status === 'pending';
      if (isPending) {
        pendingContainerIds.add(container.id);
      }

      // Create edge outline for this container (color varies by status, size, and pending state)
      const edges = createContainerEdges(containerLength, containerHeight, containerWidth, x, y, z, isLaden, size, isPending);
      scene.value.add(edges);
      edgeLines.push(edges);

      // Only create floating label for TOP container in each stack (reduces clutter)
      if (topContainerIds.has(container.id)) {
        const labelY = y + containerHeight / 2 + 1.2; // Above container top
        const label = createContainerLabel(container.container_number, x, labelY, z);
        label.visible = showLabels.value;
        scene.value.add(label);
        labelSprites.push(label);
      }

      // Create wall text for EVERY container (visible from the side)
      const wallText = createWallText(
        container.container_number,
        x,
        y,
        z,
        containerLength,
        containerHeight,
        containerWidth,
        isLaden
      );
      wallText.visible = showWallText.value;
      scene.value.add(wallText);
      wallTextMeshes.push(wallText);
    }

    // Update counts and mark matrices dirty
    (Object.keys(meshes.value) as MeshKey[]).forEach(key => {
      const mesh = meshes.value![key];
      mesh.count = counts[key];
      mesh.instanceMatrix.needsUpdate = true;

      // CRITICAL: Recompute bounding sphere for raycasting to work!
      // InstancedMesh uses the original geometry's bounding sphere for ray tests.
      // After positioning instances across the yard, we must update it.
      if (mesh.count > 0) {
        mesh.computeBoundingSphere();
      }
    });

    // Apply initial colors (including pending containers in solid orange)
    applyColorMode();

    // Pending containers now use solid orange color (no animation)
    // Color is applied via getContainerBaseColor() → CONTAINER_COLORS.PENDING
  }

  // Placement preview - ghost container at suggested position
  let previewMesh: THREE.Mesh | null = null;

  function showPlacementPreview(position: Position, isoType: string): void {
    hidePlacementPreview();
    if (!scene.value) return;

    const size = getContainerSize(isoType);
    const hc = isHighCube(isoType);
    const dimKey = hc
      ? (size === '20ft' ? '20ft_HC' : '40ft_HC')
      : (size === '20ft' ? '20ft' : '40ft');

    const dimensions = CONTAINER_DIMENSIONS[dimKey as keyof typeof CONTAINER_DIMENSIONS];
    const zoneLayout = getZoneLayout(position.zone as ZoneCode);

    // Create semi-transparent geometry
    const geometry = new THREE.BoxGeometry(
      dimensions.length,
      dimensions.height,
      dimensions.width
    );
    const material = new THREE.MeshLambertMaterial({
      color: 0xfaad14, // Gold color for preview
      transparent: true,
      opacity: 0.6,
    });

    previewMesh = new THREE.Mesh(geometry, material);

    // Calculate position (same logic as regular containers)
    // Uses sub_slot for 20ft containers
    let x: number;
    const subSlot = position.sub_slot || 'A';

    if (size === '20ft') {
      const bayStartX = zoneLayout.xOffset + (position.bay - 1) * SPACING.bay;
      if (subSlot === 'A') {
        x = bayStartX + dimensions.length / 2 + SPACING.gap;
      } else {
        x = bayStartX + dimensions.length + SPACING.gap * 2 + dimensions.length / 2;
      }
    } else {
      x = zoneLayout.xOffset + (position.bay - 0.5) * SPACING.bay;
    }
    const y = (position.tier - 1) * SPACING.tier + dimensions.height / 2;
    const z = zoneLayout.zOffset + (position.row - 0.5) * SPACING.row;

    previewMesh.position.set(x, y, z);
    previewMesh.castShadow = true;

    scene.value.add(previewMesh);
  }

  function hidePlacementPreview(): void {
    if (previewMesh) {
      scene.value?.remove(previewMesh);
      previewMesh.geometry.dispose();
      (previewMesh.material as THREE.Material).dispose();
      previewMesh = null;
    }
  }

  // Track current hovered container for color management
  let currentHoveredId: number | null = null;
  let currentSelectedId: number | null = null;

  // Get the base color for a container based on current color mode
  function getContainerBaseColor(container: ContainerPlacement): number {
    // Pending containers (work order created) always show yellow regardless of color mode
    if (container.placement_status === 'pending') {
      return CONTAINER_COLORS.PENDING;
    }

    if (colorMode.value === 'dwell_time') {
      return getDwellTimeColor(container.dwell_time_days);
    }
    // Status mode with size-specific colors: 20ft = bright, 40ft = darker
    const isLaden = container.status === 'LADEN';
    const size = getContainerSize(container.iso_type);
    return getContainerColor(isLaden, size);
  }

  // Recolor all containers based on current color mode and company filter
  function applyColorMode(): void {
    if (!meshes.value) return;

    // Reset colors for all containers based on color mode
    for (const [id, info] of containerMap) {
      const container = containerById.get(id);
      if (!container) continue;

      const mesh = meshes.value[info.meshKey];
      const baseColorHex = getContainerBaseColor(container);
      const color = new THREE.Color(baseColorHex);

      // Dim containers during placement mode for visual clarity
      // Position markers become more prominent when containers are faded
      // EXCEPT: Pending containers stay bright orange to stand out
      const isPending = container.placement_status === 'pending';
      if (placementModeActive && !isPending) {
        color.lerp(new THREE.Color(0x888888), 0.7); // 70% toward gray for strong dimming
      }

      // Apply company filter: dim containers that don't match the selected company
      // EXCEPT: Pending containers always stay bright
      if (filteredCompanyName.value && !isPending) {
        const containerCompany = container.company_name || 'Без компании';
        if (containerCompany !== filteredCompanyName.value) {
          // Blend 70% toward gray to dim non-matching containers
          color.lerp(new THREE.Color(0xcccccc), 0.7);
        }
      }

      mesh.setColorAt(info.instanceId, color);
    }

    // Update all meshes
    (Object.keys(meshes.value) as MeshKey[]).forEach(key => {
      if (meshes.value![key].instanceColor) {
        meshes.value![key].instanceColor!.needsUpdate = true;
      }
    });

    // Re-apply hover/selection highlights
    applyHighlights();
  }

  // Apply hover and selection highlights on top of base colors
  function applyHighlights(): void {
    if (!meshes.value) return;

    // Apply hover highlight (orange) - lower priority
    if (currentHoveredId !== null && currentHoveredId !== currentSelectedId) {
      const info = containerMap.get(currentHoveredId);
      if (info && meshes.value[info.meshKey]) {
        const mesh = meshes.value[info.meshKey];
        mesh.setColorAt(info.instanceId, new THREE.Color(CONTAINER_COLORS.HOVERED));
        if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
      }
    }

    // Apply selection highlight (gold) - higher priority
    if (currentSelectedId !== null) {
      const info = containerMap.get(currentSelectedId);
      if (info && meshes.value[info.meshKey]) {
        const mesh = meshes.value[info.meshKey];
        mesh.setColorAt(info.instanceId, new THREE.Color(CONTAINER_COLORS.SELECTED));
        if (mesh.instanceColor) mesh.instanceColor.needsUpdate = true;
      }
    }
  }

  // Set color mode and recolor all containers
  function setColorMode(mode: ColorMode): void {
    colorMode.value = mode;
    applyColorMode();
  }

  // Apply company filter (dim non-matching containers)
  function applyCompanyFilter(companyName: string | null): void {
    filteredCompanyName.value = companyName;
    applyColorMode(); // Re-apply colors with filter
  }

  // Stop pending container animation (cleanup function)
  // Note: Pulsing animation removed - pending containers now use solid orange color
  function stopPendingAnimation(): void {
    if (pendingAnimationId !== null) {
      cancelAnimationFrame(pendingAnimationId);
      pendingAnimationId = null;
    }
  }

  // Enter placement mode: hide labels/wall text and dim containers
  // This makes position markers more prominent for easier placement
  function enterPlacementModeVisuals(): void {
    // Save current label/wallText visibility state
    preplacementLabelsState = showLabels.value;
    preplacementWallTextState = showWallText.value;

    // Hide labels and wall text for visual clarity
    toggleLabels(false);
    toggleWallText(false);

    // Mark mode active and reapply colors with dimming
    placementModeActive = true;
    applyColorMode();
  }

  // Exit placement mode: restore labels/wall text and container colors
  function exitPlacementModeVisuals(): void {
    // Restore previous label/wallText visibility
    toggleLabels(preplacementLabelsState);
    toggleWallText(preplacementWallTextState);

    // Remove dimming
    placementModeActive = false;
    applyColorMode();
  }

  function highlightContainer(containerId: number | null, isHover: boolean = false): void {
    if (!meshes.value) return;

    // Update tracking
    if (isHover) {
      currentHoveredId = containerId;
    } else {
      currentSelectedId = containerId;
    }

    // Reset all colors based on current color mode
    applyColorMode();
  }

  // Separate function for hover highlighting
  function hoverContainer(containerId: number | null): void {
    highlightContainer(containerId, true);
  }

  // Separate function for selection highlighting
  function selectContainer(containerId: number | null): void {
    highlightContainer(containerId, false);
  }

  function getContainerAtPoint(
    clientX: number,
    clientY: number,
    canvas: HTMLCanvasElement,
    camera: THREE.Camera
  ): ContainerPlacement | null {
    if (!meshes.value) {
      console.warn('getContainerAtPoint: meshes.value is null');
      return null;
    }

    const rect = canvas.getBoundingClientRect();
    mouse.x = ((clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);
    const allMeshes = Object.values(meshes.value);

    // Debug logging removed - was too noisy

    const intersects = raycaster.intersectObjects(allMeshes);

    const hit = intersects[0];
    if (!hit) {
      return null;
    }

    if (hit.instanceId === undefined || !hit.object) return null;

    // Find container by instance ID and mesh
    for (const [id, info] of containerMap) {
      if (info.instanceId === hit.instanceId && meshes.value[info.meshKey] === hit.object) {
        return containerById.get(id) ?? null;
      }
    }

    return null;
  }

  // ─────────────────────────────────────────────────────────────────────────────
  // Position Markers - For visualizing placement suggestions
  // ─────────────────────────────────────────────────────────────────────────────

  // Track marker meshes and their metadata
  const positionMarkers: THREE.Group[] = [];
  const markerLabels: THREE.Sprite[] = [];
  const availableMarkers: THREE.Group[] = []; // Separate array for lightweight gray markers
  let currentHighlightedMarkerIndex: number | null = null; // -1 = primary, 0+ = alternatives, -2 = available
  let selectedMarkerIndex: number | null = null;
  let pulseAnimationId: number | null = null;

  // Shared material for lightweight markers (performance optimization)
  let sharedGrayEdgeMaterial: THREE.LineBasicMaterial | null = null;

  // Get dimension key for a container based on ISO type
  function getDimensionKey(isoType: string): keyof typeof CONTAINER_DIMENSIONS {
    const size = getContainerSize(isoType);
    const hc = isHighCube(isoType);
    if (size === '20ft') {
      return hc ? '20ft_HC' : '20ft';
    }
    return hc ? '40ft_HC' : '40ft';
  }

  // Create a single position marker (semi-transparent box with edges)
  function createPositionMarker(
    position: Position,
    markerData: PositionMarkerData,
    color: number,
    isoType: string = '45G1'
  ): THREE.Group {
    const group = new THREE.Group();
    group.userData = markerData;

    const dimensions = CONTAINER_DIMENSIONS[getDimensionKey(isoType)];

    // Scale to 95% to show slot boundaries
    const scale = 0.95;
    const geometry = new THREE.BoxGeometry(
      dimensions.length * scale,
      dimensions.height * scale,
      dimensions.width * scale
    );

    // Semi-transparent fill - increased opacity for better visibility
    const material = new THREE.MeshLambertMaterial({
      color,
      transparent: true,
      opacity: 0.6,
      depthWrite: false,
    });

    const mesh = new THREE.Mesh(geometry, material);
    group.add(mesh);

    // Add edges for definition - high opacity with depth write disabled
    const edgesGeometry = new THREE.EdgesGeometry(geometry);
    const edgesMaterial = new THREE.LineBasicMaterial({
      color,
      linewidth: 2,
      transparent: true,
      opacity: 0.95,
      depthWrite: false,
    });
    const edges = new THREE.LineSegments(edgesGeometry, edgesMaterial);
    group.add(edges);

    // Position the group
    const worldPos = positionToWorld(position, isoType);
    group.position.set(worldPos.x, worldPos.y, worldPos.z);

    return group;
  }

  // Create a floating label for a marker
  function createMarkerLabel(
    text: string,
    x: number,
    y: number,
    z: number,
    isPrimary: boolean
  ): THREE.Sprite {
    const canvas = document.createElement('canvas');
    const context = canvas.getContext('2d')!;

    canvas.width = 256;
    canvas.height = 64;

    // Background
    context.fillStyle = isPrimary ? 'rgba(82, 196, 26, 0.9)' : 'rgba(22, 119, 255, 0.9)';
    context.beginPath();
    context.roundRect(4, 4, 248, 56, 8);
    context.fill();

    // Text
    context.fillStyle = '#ffffff';
    context.font = 'bold 24px monospace';
    context.textAlign = 'center';
    context.textBaseline = 'middle';

    const displayText = isPrimary ? `★ ${text}` : text;
    context.fillText(displayText, 128, 32);

    const texture = new THREE.CanvasTexture(canvas);
    texture.minFilter = THREE.LinearFilter;
    texture.magFilter = THREE.LinearFilter;

    const material = new THREE.SpriteMaterial({
      map: texture,
      transparent: true,
      depthTest: false,
      depthWrite: false,
    });

    const sprite = new THREE.Sprite(material);
    sprite.position.set(x, y, z);
    sprite.scale.set(6, 1.5, 1);

    return sprite;
  }

  // Create a lightweight marker for available (non-recommended) positions
  // Uses wireframe only (no fill) and shared material for performance
  function createLightweightMarker(
    position: Position,
    markerData: PositionMarkerData,
    isoType: string = '45G1'
  ): THREE.Group {
    const group = new THREE.Group();
    group.userData = markerData;

    const dimensions = CONTAINER_DIMENSIONS[getDimensionKey(isoType)];

    // Smaller scale (0.85) to differentiate from recommendations (0.95)
    const scale = 0.85;
    const geometry = new THREE.BoxGeometry(
      dimensions.length * scale,
      dimensions.height * scale,
      dimensions.width * scale
    );

    // Create shared material if not exists (reused for all gray markers)
    // Increased opacity for better visibility against dimmed containers
    if (!sharedGrayEdgeMaterial) {
      sharedGrayEdgeMaterial = new THREE.LineBasicMaterial({
        color: MARKER_COLORS.AVAILABLE,
        linewidth: 1,
        transparent: true,
        opacity: 0.9,
        depthWrite: false,
      });
    }

    // Add semi-transparent fill for better visibility (was wireframe-only)
    const fillMaterial = new THREE.MeshLambertMaterial({
      color: MARKER_COLORS.AVAILABLE,
      transparent: true,
      opacity: 0.3,
      depthWrite: false,
    });
    const fillMesh = new THREE.Mesh(geometry.clone(), fillMaterial);
    group.add(fillMesh);

    // Add edges for outline definition
    const edgesGeometry = new THREE.EdgesGeometry(geometry);
    const edges = new THREE.LineSegments(edgesGeometry, sharedGrayEdgeMaterial);
    group.add(edges);

    // Position the group
    const worldPos = positionToWorld(position, isoType);
    group.position.set(worldPos.x, worldPos.y, worldPos.z);

    // Dispose the box geometry (edges geometry keeps its own copy)
    geometry.dispose();

    return group;
  }

  // Show position markers for a placement suggestion
  function showPositionMarkers(
    suggestion: SuggestionResponse,
    isoType: string = '45G1',
    availablePositions: Position[] = []
  ): void {
    hidePositionMarkers(); // Clear any existing markers

    if (!scene.value) return;

    const dimensions = CONTAINER_DIMENSIONS[getDimensionKey(isoType)];

    // FIRST: Create lightweight gray markers for all available positions
    // Rendered first so colored markers appear ON TOP
    for (const availablePos of availablePositions) {
      const availableData: PositionMarkerData = {
        type: 'available',
        index: -2, // Special index for available (non-recommended) positions
        position: availablePos,
        coordinate: availablePos.coordinate || formatCoordinate(availablePos),
      };
      const availableMarker = createLightweightMarker(availablePos, availableData, isoType);
      scene.value.add(availableMarker);
      availableMarkers.push(availableMarker);
    }

    // Create primary marker (green)
    const primaryData: PositionMarkerData = {
      type: 'primary',
      index: -1,
      position: suggestion.suggested_position,
      coordinate: suggestion.suggested_position.coordinate || formatCoordinate(suggestion.suggested_position),
    };
    const primaryMarker = createPositionMarker(
      suggestion.suggested_position,
      primaryData,
      MARKER_COLORS.PRIMARY,
      isoType
    );
    scene.value.add(primaryMarker);
    positionMarkers.push(primaryMarker);

    // Add primary label
    const primaryWorldPos = positionToWorld(suggestion.suggested_position, isoType);
    const primaryLabel = createMarkerLabel(
      primaryData.coordinate,
      primaryWorldPos.x,
      primaryWorldPos.y + dimensions.height / 2 + 1.5,
      primaryWorldPos.z,
      true
    );
    scene.value.add(primaryLabel);
    markerLabels.push(primaryLabel);

    // Create alternative markers (blue)
    suggestion.alternatives.forEach((altPosition, index) => {
      const altData: PositionMarkerData = {
        type: 'alternative',
        index,
        position: altPosition,
        coordinate: altPosition.coordinate || formatCoordinate(altPosition),
      };
      const altMarker = createPositionMarker(
        altPosition,
        altData,
        MARKER_COLORS.ALTERNATIVE,
        isoType
      );
      scene.value!.add(altMarker);
      positionMarkers.push(altMarker);

      // Add alternative label
      const altWorldPos = positionToWorld(altPosition, isoType);
      const altLabel = createMarkerLabel(
        altData.coordinate,
        altWorldPos.x,
        altWorldPos.y + dimensions.height / 2 + 1.5,
        altWorldPos.z,
        false
      );
      scene.value!.add(altLabel);
      markerLabels.push(altLabel);
    });

    // Start pulsing animation for primary marker
    startPulseAnimation();
  }

  // Format position to coordinate string (fallback if not provided)
  function formatCoordinate(pos: Position): string {
    return `${pos.zone}-R${String(pos.row).padStart(2, '0')}-B${String(pos.bay).padStart(2, '0')}-T${pos.tier}-${pos.sub_slot || 'A'}`;
  }

  // Start pulsing animation for primary marker
  function startPulseAnimation(): void {
    if (pulseAnimationId !== null) return; // Already running

    let phase = 0;
    const animate = () => {
      if (positionMarkers.length === 0) {
        stopPulseAnimation();
        return;
      }

      // Primary marker is at index 0
      const primaryMarker = positionMarkers[0];
      if (!primaryMarker) {
        stopPulseAnimation();
        return;
      }

      // Pulse scale between 0.95 and 1.05
      phase += 0.08;
      const scale = 1 + Math.sin(phase) * 0.05;
      primaryMarker.scale.setScalar(scale);

      // Pulse opacity between 0.3 and 0.6
      const opacity = 0.45 + Math.sin(phase) * 0.15;
      primaryMarker.traverse((child) => {
        if (child instanceof THREE.Mesh) {
          (child.material as THREE.MeshLambertMaterial).opacity = opacity;
        }
      });

      pulseAnimationId = requestAnimationFrame(animate);
    };

    pulseAnimationId = requestAnimationFrame(animate);
  }

  // Stop pulsing animation
  function stopPulseAnimation(): void {
    if (pulseAnimationId !== null) {
      cancelAnimationFrame(pulseAnimationId);
      pulseAnimationId = null;
    }
  }

  // Hide and dispose all position markers
  function hidePositionMarkers(): void {
    // Stop pulsing animation
    stopPulseAnimation();

    // Dispose marker groups (colored markers - green/blue)
    for (const group of positionMarkers) {
      group.traverse((child) => {
        if (child instanceof THREE.Mesh) {
          child.geometry.dispose();
          (child.material as THREE.Material).dispose();
        } else if (child instanceof THREE.LineSegments) {
          child.geometry.dispose();
          (child.material as THREE.Material).dispose();
        }
      });
      scene.value?.remove(group);
    }
    positionMarkers.length = 0;

    // Dispose available markers (gray markers with fill + wireframe)
    // Note: shared edge material is NOT disposed here - it's reused
    for (const group of availableMarkers) {
      group.traverse((child) => {
        if (child instanceof THREE.Mesh) {
          child.geometry.dispose();
          (child.material as THREE.Material).dispose();
        } else if (child instanceof THREE.LineSegments) {
          child.geometry.dispose();
          // Don't dispose sharedGrayEdgeMaterial - it's reused
        }
      });
      scene.value?.remove(group);
    }
    availableMarkers.length = 0;

    // Dispose labels
    for (const sprite of markerLabels) {
      if (sprite.material.map) {
        sprite.material.map.dispose();
      }
      sprite.material.dispose();
      scene.value?.remove(sprite);
    }
    markerLabels.length = 0;

    currentHighlightedMarkerIndex = null;
    selectedMarkerIndex = null;
  }

  // Track currently highlighted available marker (separate from position markers)
  let currentHighlightedAvailableMarker: THREE.Group | null = null;

  // Highlight a marker on hover (changes color to green)
  function highlightMarker(markerIndex: number | null, availableMarkerGroup?: THREE.Group | null): void {
    if (!scene.value) return;

    // Reset previous available marker highlight (restore to semi-transparent)
    if (currentHighlightedAvailableMarker) {
      setMarkerColor(currentHighlightedAvailableMarker, MARKER_COLORS.AVAILABLE, false);
      currentHighlightedAvailableMarker = null;
    }

    // Reset previous position marker highlight
    if (currentHighlightedMarkerIndex !== null && positionMarkers.length > 0) {
      const prevIndex = currentHighlightedMarkerIndex === -1 ? 0 : currentHighlightedMarkerIndex + 1;
      const prevMarker = positionMarkers[prevIndex];
      if (prevMarker) {
        const isSelected = selectedMarkerIndex === currentHighlightedMarkerIndex;
        const isPrimary = currentHighlightedMarkerIndex === -1;

        // Determine color based on selection state
        let color: number;
        if (isSelected) {
          color = MARKER_COLORS.SELECTED;
        } else if (isPrimary) {
          color = MARKER_COLORS.PRIMARY;
        } else {
          color = MARKER_COLORS.ALTERNATIVE;
        }
        setMarkerColor(prevMarker, color);
      }
    }

    currentHighlightedMarkerIndex = markerIndex;

    // Handle available markers (index -2) - make SOLID green on hover
    if (markerIndex === -2 && availableMarkerGroup) {
      setMarkerColor(availableMarkerGroup, MARKER_COLORS.HOVERED, true);
      currentHighlightedAvailableMarker = availableMarkerGroup;
      return;
    }

    // Handle position markers (green/blue) - make SOLID on hover
    if (markerIndex !== null && positionMarkers.length > 0) {
      const index = markerIndex === -1 ? 0 : markerIndex + 1;
      const marker = positionMarkers[index];
      if (marker) {
        setMarkerColor(marker, MARKER_COLORS.HOVERED, true);
      }
    }
  }

  // Select a marker (changes color to purple, persists until changed)
  function selectMarker(markerIndex: number | null): void {
    if (!scene.value || positionMarkers.length === 0) return;

    // Reset previous selection
    if (selectedMarkerIndex !== null) {
      const prevIndex = selectedMarkerIndex === -1 ? 0 : selectedMarkerIndex + 1;
      const prevMarker = positionMarkers[prevIndex];
      if (prevMarker) {
        const isPrimary = selectedMarkerIndex === -1;
        const color = isPrimary ? MARKER_COLORS.PRIMARY : MARKER_COLORS.ALTERNATIVE;
        setMarkerColor(prevMarker, color);
      }
    }

    // Apply new selection
    selectedMarkerIndex = markerIndex;
    if (markerIndex !== null) {
      const index = markerIndex === -1 ? 0 : markerIndex + 1;
      const marker = positionMarkers[index];
      if (marker) {
        setMarkerColor(marker, MARKER_COLORS.SELECTED);
      }
    }
  }

  // Helper to set marker color and optionally opacity (for hover highlight)
  // Note: Only changes fill color, NOT edges - edges use shared material and would affect all markers
  function setMarkerColor(group: THREE.Group, color: number, solidFill?: boolean): void {
    group.traverse((child) => {
      if (child instanceof THREE.Mesh) {
        const mat = child.material as THREE.MeshLambertMaterial;
        mat.color.setHex(color);
        // Make fully opaque when solidFill is true (for hover effect)
        if (solidFill !== undefined) {
          mat.opacity = solidFill ? 0.9 : 0.3; // 0.3 is default for gray, 0.6 for colored
        }
      }
      // Don't change edge colors - they use shared materials and it causes visual noise
    });
  }

  // Result type for getMarkerAtPoint - includes group reference for hover highlighting
  interface MarkerHitResult {
    data: PositionMarkerData;
    group: THREE.Group;
  }

  // Get marker at screen point (for click/hover detection)
  function getMarkerAtPoint(
    clientX: number,
    clientY: number,
    canvas: HTMLCanvasElement,
    camera: THREE.Camera
  ): MarkerHitResult | null {
    if (positionMarkers.length === 0 && availableMarkers.length === 0) {
      return null;
    }

    const rect = canvas.getBoundingClientRect();
    mouse.x = ((clientX - rect.left) / rect.width) * 2 - 1;
    mouse.y = -((clientY - rect.top) / rect.height) * 2 + 1;

    raycaster.setFromCamera(mouse, camera);

    // Collect raycastable objects: meshes from colored markers, meshes+lines from available markers
    const markerObjects: THREE.Object3D[] = [];

    for (const group of positionMarkers) {
      group.traverse((child) => {
        if (child instanceof THREE.Mesh) {
          markerObjects.push(child);
        }
      });
    }

    for (const group of availableMarkers) {
      group.traverse((child) => {
        if (child instanceof THREE.Mesh || child instanceof THREE.LineSegments) {
          markerObjects.push(child);
        }
      });
    }

    const intersects = raycaster.intersectObjects(markerObjects, false);
    const firstHit = intersects[0];
    if (!firstHit) {
      return null;
    }

    // Traverse up to find parent group with marker userData
    let current: THREE.Object3D | null = firstHit.object;
    while (current && !current.userData?.type) {
      current = current.parent;
    }

    if (current?.userData?.type) {
      return {
        data: current.userData as PositionMarkerData,
        group: current as THREE.Group,
      };
    }
    return null;
  }

  function dispose(): void {
    stopPulseAnimation();
    stopPendingAnimation();
    pendingContainerIds.clear();
    if (meshes.value) {
      Object.values(meshes.value).forEach(mesh => mesh.dispose());
    }
    clearLabels();
    clearWallText();
    clearEdgeLines();
    hidePositionMarkers();
    containerMap.clear();
    containerById.clear();

    // Dispose shared gray edge material
    if (sharedGrayEdgeMaterial) {
      sharedGrayEdgeMaterial.dispose();
      sharedGrayEdgeMaterial = null;
    }
  }

  return {
    meshes,
    showLabels,
    showWallText,
    colorMode,
    filteredCompanyName,
    initMeshes,
    updateContainers,
    highlightContainer,
    hoverContainer,
    selectContainer,
    getContainerAtPoint,
    toggleLabels,
    toggleWallText,
    setColorMode,
    applyCompanyFilter,
    // Placement mode visual functions
    enterPlacementModeVisuals,
    exitPlacementModeVisuals,
    showPlacementPreview,
    hidePlacementPreview,
    // Position marker functions
    showPositionMarkers,
    hidePositionMarkers,
    highlightMarker,
    selectMarker,
    getMarkerAtPoint,
    dispose,
  };
}
