import React, { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js'
import { OrbitControls } from 'three/addons/controls/OrbitControls.js'

export default function CadViewer({ modelUrl }) {
  const mountRef = useRef(null)

  useEffect(() => {
    if (!modelUrl || !mountRef.current) return
    const container = mountRef.current
    const width = container.clientWidth || 800
    const height = container.clientHeight || 380

    const scene = new THREE.Scene()
    scene.background = new THREE.Color(0x111111)

    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 5000)
    camera.position.set(160, 90, 160)

    const renderer = new THREE.WebGLRenderer({ antialias: true })
    renderer.setSize(width, height)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    container.innerHTML = ''
    container.appendChild(renderer.domElement)

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.target.set(0, 0, 0)

    scene.add(new THREE.AmbientLight(0xffffff, 1.2))
    const directional = new THREE.DirectionalLight(0xffffff, 2.0)
    directional.position.set(120, 200, 160)
    scene.add(directional)

    let frameId
    const animate = () => {
      frameId = requestAnimationFrame(animate)
      controls.update()
      renderer.render(scene, camera)
    }
    animate()

    const loader = new GLTFLoader()
    loader.load(
      modelUrl,
      (gltf) => {
        const model = gltf.scene
        const box = new THREE.Box3().setFromObject(model)
        const center = box.getCenter(new THREE.Vector3())
        model.position.sub(center)
        scene.add(model)
        controls.target.set(0, 0, 0)
      },
      undefined,
      (loadError) => { console.warn('GLB load failed:', loadError) }
    )

    const handleResize = () => {
      const w = container.clientWidth || 800
      const h = container.clientHeight || 380
      camera.aspect = w / h
      camera.updateProjectionMatrix()
      renderer.setSize(w, h)
    }
    window.addEventListener('resize', handleResize)

    return () => {
      cancelAnimationFrame(frameId)
      window.removeEventListener('resize', handleResize)
      controls.dispose()
      renderer.dispose()
    }
  }, [modelUrl])

  return (
    <section style={{ marginTop: '1.5rem' }}>
      <h2 style={{ color: '#111' }}>Parametric 3D CAD viewer</h2>
      <div
        ref={mountRef}
        className="cad-container"
        style={{ display: modelUrl ? 'block' : 'flex', alignItems: 'center', justifyContent: 'center', color: '#0f0' }}
      >
        {!modelUrl && <span>[Awaiting GLB generation…]</span>}
      </div>
    </section>
  )
}
