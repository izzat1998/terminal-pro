---
name: threejs
description: Three.js consolidated reference — scene setup, geometry, materials, lighting, interaction, animation, shaders, loaders, post-processing. Use when working on any 3D feature (yard visualization, container rendering, camera controls).
---

# Three.js — Consolidated Reference

## Scene Setup

```javascript
import * as THREE from 'three';

const scene = new THREE.Scene();
scene.background = new THREE.Color(0xf0f0f0);

const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 2000);
camera.position.set(0, 50, 100);

const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
renderer.setSize(width, height);
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
container.appendChild(renderer.domElement);

// Animation loop
const clock = new THREE.Clock();
function animate() {
  requestAnimationFrame(animate);
  const delta = clock.getDelta();
  // Update controls, mixers, etc.
  renderer.render(scene, camera);
}
animate();

// Resize handler
window.addEventListener('resize', () => {
  camera.aspect = container.clientWidth / container.clientHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(container.clientWidth, container.clientHeight);
});
```

### Cleanup (critical in Vue/React)
```javascript
function dispose() {
  renderer.dispose();
  scene.traverse((obj) => {
    if (obj.geometry) obj.geometry.dispose();
    if (obj.material) {
      if (Array.isArray(obj.material)) obj.material.forEach(m => m.dispose());
      else obj.material.dispose();
    }
  });
}
// Call in onUnmounted() / useEffect cleanup
```

## Cameras

```javascript
// Perspective (3D scenes)
new THREE.PerspectiveCamera(fov, aspect, near, far);

// Orthographic (2D/top-down, yard map view)
const frustum = 50;
new THREE.OrthographicCamera(-frustum * aspect, frustum * aspect, frustum, -frustum, 0.1, 2000);

// Camera controls
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.dampingFactor = 0.05;
controls.maxPolarAngle = Math.PI / 2.1; // Prevent going below ground
controls.minDistance = 10;
controls.maxDistance = 500;
// Call controls.update() in animation loop
```

## Geometry

### Built-in Shapes
```javascript
new THREE.BoxGeometry(width, height, depth);       // Containers
new THREE.PlaneGeometry(width, height, segW, segH); // Ground plane
new THREE.CylinderGeometry(rTop, rBottom, h, seg);  // Pillars
new THREE.CircleGeometry(radius, segments);          // Markers
```

### InstancedMesh (1000+ identical objects)
```javascript
// Perfect for rendering many containers with different positions/colors
const geometry = new THREE.BoxGeometry(6.1, 2.6, 2.44); // 20ft container
const material = new THREE.MeshStandardMaterial();
const mesh = new THREE.InstancedMesh(geometry, material, count);

const dummy = new THREE.Object3D();
const color = new THREE.Color();
for (let i = 0; i < count; i++) {
  dummy.position.set(x, y, z);
  dummy.rotation.set(0, angle, 0);
  dummy.updateMatrix();
  mesh.setMatrixAt(i, dummy.matrix);
  mesh.setColorAt(i, color.set(getColorForStatus(status)));
}
mesh.instanceMatrix.needsUpdate = true;
mesh.instanceColor.needsUpdate = true;
scene.add(mesh);
```

### Custom BufferGeometry
```javascript
const geometry = new THREE.BufferGeometry();
const vertices = new Float32Array([...]);
const indices = new Uint16Array([...]);
geometry.setAttribute('position', new THREE.BufferAttribute(vertices, 3));
geometry.setIndex(new THREE.BufferAttribute(indices, 1));
geometry.computeVertexNormals();
```

## Materials

```javascript
// Standard PBR (most common)
new THREE.MeshStandardMaterial({
  color: 0x2194ce,
  roughness: 0.7,
  metalness: 0.1,
  transparent: true,
  opacity: 0.9,
});

// Basic (no lighting, flat color — labels, wireframes)
new THREE.MeshBasicMaterial({ color: 0xff0000, wireframe: true });

// Line material
new THREE.LineBasicMaterial({ color: 0x000000, linewidth: 1 });
new THREE.LineDashedMaterial({ color: 0x999999, dashSize: 3, gapSize: 1 });

// Material pooling (reuse by key to reduce draw calls)
const materialCache = new Map<string, THREE.Material>();
function getMaterial(color: string): THREE.MeshStandardMaterial {
  if (!materialCache.has(color)) {
    materialCache.set(color, new THREE.MeshStandardMaterial({ color }));
  }
  return materialCache.get(color)!;
}
```

## Lighting

```javascript
// Ambient (base illumination)
scene.add(new THREE.AmbientLight(0xffffff, 0.4));

// Directional (sun-like, casts shadows)
const sun = new THREE.DirectionalLight(0xffffff, 0.8);
sun.position.set(50, 100, 50);
sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
sun.shadow.camera.near = 1;
sun.shadow.camera.far = 300;
// Tight frustum for better shadow quality
sun.shadow.camera.left = -100;
sun.shadow.camera.right = 100;
sun.shadow.camera.top = 100;
sun.shadow.camera.bottom = -100;
sun.shadow.bias = -0.0001;
scene.add(sun);

// Hemisphere (sky/ground ambient)
scene.add(new THREE.HemisphereLight(0x87ceeb, 0x362907, 0.3));
```

## Interaction (Raycasting)

```javascript
const raycaster = new THREE.Raycaster();
const mouse = new THREE.Vector2();

function onPointerClick(event: PointerEvent) {
  const rect = renderer.domElement.getBoundingClientRect();
  mouse.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
  mouse.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

  raycaster.setFromCamera(mouse, camera);
  const intersects = raycaster.intersectObjects(selectableObjects, false);

  if (intersects.length > 0) {
    const hit = intersects[0].object;
    // For InstancedMesh: intersects[0].instanceId gives the index
    handleSelection(hit, intersects[0].instanceId);
  }
}
renderer.domElement.addEventListener('pointerdown', onPointerClick);

// Hover effect
function onPointerMove(event: PointerEvent) {
  // Same mouse calculation...
  raycaster.setFromCamera(mouse, camera);
  const intersects = raycaster.intersectObjects(selectableObjects, false);
  renderer.domElement.style.cursor = intersects.length > 0 ? 'pointer' : 'default';
}

// World-to-screen (for HTML labels over 3D objects)
function toScreenPosition(worldPos: THREE.Vector3, camera: THREE.Camera, canvas: HTMLElement) {
  const projected = worldPos.clone().project(camera);
  return {
    x: (projected.x * 0.5 + 0.5) * canvas.clientWidth,
    y: (-projected.y * 0.5 + 0.5) * canvas.clientHeight,
  };
}
```

## Asset Loading

```javascript
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

// Promise wrapper
function loadGLTF(url: string): Promise<THREE.Group> {
  const loader = new GLTFLoader();
  return new Promise((resolve, reject) => {
    loader.load(url, (gltf) => {
      gltf.scene.traverse((child) => {
        if (child.isMesh) {
          child.castShadow = true;
          child.receiveShadow = true;
        }
      });
      resolve(gltf.scene);
    }, undefined, reject);
  });
}

// Loading manager for progress
const manager = new THREE.LoadingManager();
manager.onProgress = (url, loaded, total) => {
  console.log(`Loading: ${(loaded / total * 100).toFixed(0)}%`);
};

// Texture loading
const textureLoader = new THREE.TextureLoader(manager);
function loadTexture(url: string): Promise<THREE.Texture> {
  return new Promise((resolve, reject) => {
    textureLoader.load(url, (tex) => {
      tex.colorSpace = THREE.SRGBColorSpace; // For color textures
      resolve(tex);
    }, undefined, reject);
  });
}
```

## Animation

```javascript
import { AnimationMixer } from 'three';

// GLTF animations
const mixer = new AnimationMixer(model);
const action = mixer.clipAction(gltf.animations[0]);
action.play();
// In animation loop: mixer.update(delta);

// Crossfade
function crossfade(from: THREE.AnimationAction, to: THREE.AnimationAction, duration = 0.3) {
  to.reset().setEffectiveWeight(1).play();
  from.crossFadeTo(to, duration, true);
}

// Procedural animation (smooth interpolation)
function animateToPosition(object: THREE.Object3D, target: THREE.Vector3, speed = 0.05) {
  object.position.lerp(target, speed); // Call each frame
}

// Spring physics
class Spring {
  value = 0; velocity = 0;
  constructor(public stiffness = 0.1, public damping = 0.8) {}
  update(target: number) {
    this.velocity += (target - this.value) * this.stiffness;
    this.velocity *= this.damping;
    this.value += this.velocity;
    return this.value;
  }
}
```

## Post-Processing

```javascript
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';

const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
composer.addPass(new UnrealBloomPass(
  new THREE.Vector2(width, height),
  1.5,   // strength
  0.4,   // radius
  0.85   // threshold
));

// In animation loop: composer.render() instead of renderer.render()

// FXAA (cheap anti-aliasing)
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { FXAAShader } from 'three/addons/shaders/FXAAShader.js';
const fxaa = new ShaderPass(FXAAShader);
fxaa.uniforms['resolution'].value.set(1 / width, 1 / height);
composer.addPass(fxaa);
```

## Shaders (Custom Effects)

```glsl
// Vertex shader — highlight effect
varying vec3 vNormal;
varying vec3 vViewDir;
void main() {
  vNormal = normalize(normalMatrix * normal);
  vec4 worldPos = modelMatrix * vec4(position, 1.0);
  vViewDir = normalize(cameraPosition - worldPos.xyz);
  gl_Position = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
}

// Fragment shader — fresnel rim glow
varying vec3 vNormal;
varying vec3 vViewDir;
uniform vec3 glowColor;
uniform float intensity;
void main() {
  float fresnel = pow(1.0 - dot(vNormal, vViewDir), 3.0);
  gl_FragColor = vec4(glowColor * fresnel * intensity, fresnel);
}
```

```javascript
// ShaderMaterial usage
new THREE.ShaderMaterial({
  vertexShader, fragmentShader,
  uniforms: {
    glowColor: { value: new THREE.Color(0x00ff88) },
    intensity: { value: 2.0 },
  },
  transparent: true,
  side: THREE.FrontSide,
});

// Inject into built-in material
material.onBeforeCompile = (shader) => {
  shader.uniforms.time = { value: 0 };
  shader.vertexShader = shader.vertexShader.replace(
    '#include <begin_vertex>',
    `#include <begin_vertex>
     transformed.y += sin(transformed.x * 0.5 + time) * 0.5;`
  );
};
```

## Performance Tips

| Technique | When to Use |
|-----------|------------|
| `InstancedMesh` | 100+ identical objects (containers, trees) |
| Material pooling | Many objects share same color/properties |
| `mergeGeometries()` | Static objects that never move independently |
| `frustumCulled = true` | Default; disable only for always-visible objects |
| Lower shadow map | 512 for mobile, 2048 for desktop |
| `renderer.setPixelRatio(Math.min(dpr, 2))` | Cap at 2x for high-DPI screens |
| `Object3D.layers` | Selective rendering (raycaster layers, bloom layers) |
| Dispose on unmount | ALWAYS clean up geometries, materials, textures, renderer |

## Quick Checklist

Before shipping 3D code:
- [ ] Resize handler updates camera AND renderer
- [ ] All geometries/materials/textures disposed on unmount
- [ ] Renderer disposed on unmount
- [ ] Animation loop uses `clock.getDelta()` for frame-rate independence
- [ ] Shadow camera frustum is tight (not default huge frustum)
- [ ] InstancedMesh used for repeated objects (not individual meshes)
- [ ] Material/texture reuse via caching
- [ ] `setPixelRatio(Math.min(dpr, 2))` caps retina rendering
