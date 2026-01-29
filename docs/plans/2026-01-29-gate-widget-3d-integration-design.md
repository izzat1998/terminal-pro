# Gate Widget 3D Integration Design

**Date:** 2026-01-29
**Status:** Approved
**Author:** Claude + User collaboration

## Overview

Integrate the gate camera widget into the 3D yard canvas using CSS3DRenderer, making it feel "built-in" rather than a floating HTML overlay.

## Problem Statement

Current `GateCameraWidget.vue` uses `<Teleport to="body">` to render as an HTML overlay above the 3D yard. This creates a visual disconnect - the widget feels separate from the 3D scene.

## Solution

Use Three.js `CSS3DRenderer` to render the widget with 3D perspective transforms while preserving native DOM interactions.

## Key Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Rendering approach | CSS3DRenderer | Preserves native DOM clicks, video performance, text crispness |
| Widget position | Screen-anchored (bottom-left) | Predictable position, doesn't obstruct yard view |
| Default visibility | Always visible | Operations dashboard needs constant gate monitoring |
| Hide/show mechanism | Toggle button in header | Simple, discoverable |
| 3D camera click action | Focus yard view on gate | Useful navigation, widget already visible |
| Visual style | Same dark panel + subtle 3D depth | Consistency with existing design |

## Architecture

### Rendering Stack

```
┌─────────────────────────────────────────────────────┐
│                  DOM Layer (top)                     │
│    (Regular HTML - tooltips, modals if any)         │
├─────────────────────────────────────────────────────┤
│              CSS3DRenderer Layer                     │
│    GateCameraWidget with 3D perspective transform   │
├─────────────────────────────────────────────────────┤
│              WebGLRenderer Layer                     │
│    3D Yard: containers, cameras, buildings, etc.    │
└─────────────────────────────────────────────────────┘
```

### File Changes

| File | Change Type | Description |
|------|-------------|-------------|
| `src/composables/useCSS3DRenderer.ts` | NEW | CSS3DRenderer setup & screen-anchor positioning |
| `src/components/yard/GateCameraWidget.vue` | MODIFY | Remove Teleport, add minimize/expand state |
| `src/components/yard/GateCameraWidget3D.vue` | NEW | CSS3DObject wrapper for positioning |
| `src/components/yard/GateCamera3D.vue` | MODIFY | Click emits `focusGate` instead of opening widget |
| `src/views/YardTestView.vue` | MODIFY | Integrate CSS3DRenderer layer |

## Component Details

### useCSS3DRenderer.ts

```typescript
export interface UseCSS3DRendererOptions {
  container: Ref<HTMLElement | null>
}

export function useCSS3DRenderer(options: UseCSS3DRendererOptions) {
  const renderer = shallowRef<CSS3DRenderer | null>(null)
  const scene = new THREE.Scene()

  const DOCK_POSITIONS = {
    'bottom-left': (w: number, h: number) => ({ x: -w/2 + 150, y: -h/2 + 100, z: 0 }),
    'bottom-right': (w: number, h: number) => ({ x: w/2 - 150, y: -h/2 + 100, z: 0 }),
    'top-left': (w: number, h: number) => ({ x: -w/2 + 150, y: h/2 - 100, z: 0 }),
    'top-right': (w: number, h: number) => ({ x: w/2 - 150, y: h/2 - 100, z: 0 }),
  }

  function init(): void
  function addWidget(element: HTMLElement, dock: DockPosition): CSS3DObject
  function updateSize(width: number, height: number): void
  function render(camera: THREE.Camera): void
  function dispose(): void

  return { renderer, scene, addWidget, updateSize, render, dispose }
}
```

### GateCameraWidget.vue Changes

- Remove `<Teleport to="body">` wrapper
- Replace close button with minimize/expand toggle
- Add `isMinimized` state with collapsed view (header only)
- Keep all detection logic unchanged

### GateCameraWidget3D.vue (New)

```vue
<script setup lang="ts">
import { CSS3DObject } from 'three/examples/jsm/renderers/CSS3DRenderer.js'
import GateCameraWidget from './GateCameraWidget.vue'

const props = defineProps<{
  css3DScene: THREE.Scene
  dockPosition: 'bottom-left' | 'bottom-right' | 'top-left' | 'top-right'
  gateId?: string
}>()

const widgetRef = ref<HTMLElement | null>(null)

onMounted(() => {
  const css3DObject = new CSS3DObject(widgetRef.value!)
  // Position based on dock
  props.css3DScene.add(css3DObject)
})
</script>

<template>
  <div ref="widgetRef">
    <GateCameraWidget :visible="true" :gateId="gateId" />
  </div>
</template>
```

### GateCamera3D.vue Changes

- Change click handler to emit `focusGate` event with gate position
- Remove widget-opening logic

## Implementation Phases

### Phase 1: CSS3DRenderer Foundation
- Create `useCSS3DRenderer.ts` composable
- Add CSS3DRenderer to YardTestView
- Verify dual-renderer setup works

### Phase 2: Widget Adaptation
- Modify `GateCameraWidget.vue` for minimize/expand
- Create `GateCameraWidget3D.vue` wrapper
- Style minimized state

### Phase 3: Integration
- Wire up widget via CSS3DRenderer in YardTestView
- Update `GateCamera3D.vue` click behavior
- Implement camera focus animation

### Phase 4: Polish
- Responsive dock position calculations
- Subtle 3D depth styling
- Performance testing with video feed

## Testing Checklist

- [ ] Widget renders with 3D perspective in yard view
- [ ] Widget visible by default on page load
- [ ] Minimize/expand toggle works
- [ ] Video feed plays correctly in CSS3D context
- [ ] Scan button triggers detection
- [ ] Detection results display correctly
- [ ] Clicking 3D camera focuses yard view on gate
- [ ] Widget stays in dock position during camera orbit
- [ ] No z-fighting between WebGL and CSS3D layers
- [ ] Keyboard shortcuts still work (Esc, etc.)

## Performance Considerations

- CSS3DRenderer is lightweight (just CSS transforms on DOM elements)
- Video stays as native `<video>` element (GPU-accelerated)
- No texture uploads to WebGL for the widget
- Single additional render call per frame

## Rollback Plan

If CSS3DRenderer causes issues, the current Teleport-based implementation remains functional. Changes are additive and can be feature-flagged.
