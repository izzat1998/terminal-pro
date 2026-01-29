/**
 * Three.js Utility Functions
 *
 * Provides common utilities for Three.js object management,
 * particularly for proper disposal of geometries and materials to prevent memory leaks.
 */

import * as THREE from 'three'

/**
 * Recursively dispose all geometries and materials in a Three.js object
 *
 * Call this when removing objects from a scene to prevent memory leaks.
 * Handles both single materials and material arrays.
 *
 * @param object - The Three.js Object3D to dispose
 *
 * @example
 * // When removing a group from scene
 * scene.remove(vehicleGroup)
 * disposeObject3D(vehicleGroup)
 */
export function disposeObject3D(object: THREE.Object3D): void {
  object.traverse((child) => {
    if (child instanceof THREE.Mesh) {
      // Dispose geometry
      child.geometry.dispose()

      // Dispose material(s)
      if (Array.isArray(child.material)) {
        child.material.forEach((mat) => mat.dispose())
      } else if (child.material) {
        child.material.dispose()
      }
    }

    // Handle Line objects as well
    if (child instanceof THREE.Line) {
      child.geometry.dispose()
      if (child.material instanceof THREE.Material) {
        child.material.dispose()
      }
    }

    // Handle Points
    if (child instanceof THREE.Points) {
      child.geometry.dispose()
      if (child.material instanceof THREE.Material) {
        child.material.dispose()
      }
    }
  })
}

/**
 * Remove object from parent and dispose all resources
 *
 * Convenience function that combines removal and disposal in one call.
 *
 * @param object - The Three.js Object3D to remove and dispose
 *
 * @example
 * // Clean up a mesh completely
 * removeAndDispose(cameraMesh)
 */
export function removeAndDispose(object: THREE.Object3D): void {
  // Remove from parent if attached
  if (object.parent) {
    object.parent.remove(object)
  }

  // Dispose all resources
  disposeObject3D(object)
}

/**
 * Dispose a single material (handles textures as well)
 *
 * @param material - The material to dispose
 */
export function disposeMaterial(material: THREE.Material): void {
  // Dispose any textures on the material
  if (material instanceof THREE.MeshStandardMaterial) {
    material.map?.dispose()
    material.normalMap?.dispose()
    material.roughnessMap?.dispose()
    material.metalnessMap?.dispose()
    material.aoMap?.dispose()
    material.emissiveMap?.dispose()
  } else if (material instanceof THREE.MeshBasicMaterial) {
    material.map?.dispose()
  }

  material.dispose()
}
