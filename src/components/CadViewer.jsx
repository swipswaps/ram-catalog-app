import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

export default function CadViewer() {
  const mountRef = useRef(null);

  useEffect(() => {
    if (!mountRef.current) return;
    const currentMount = mountRef.current;

    // 1. Scene Setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x020617);

    // 2. Camera & Renderer
    const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 1000);
    camera.position.set(160, 90, 160);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    currentMount.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;

    // 3. Lighting
    scene.add(new THREE.AmbientLight(0xffffff, 0.8));
    const dirLight = new THREE.DirectionalLight(0xffffff, 1.2);
    dirLight.position.set(5, 10, 7);
    scene.add(dirLight);

    // 4. Geometry (JEDEC Dimensions)
    const L = 133.35, H = 31.25, T = 1.57, G = 5.0;
    const IC = { w: 11, h: 1.2, d: 9 };
    const group = new THREE.Group();

    group.add(new THREE.Mesh(new THREE.BoxGeometry(L, T, H), new THREE.MeshStandardMaterial({ color: 0x0a5c36, roughness: 0.8 })));
    
    const gold = new THREE.Mesh(new THREE.BoxGeometry(L, T + 0.02, G), new THREE.MeshStandardMaterial({ color: 0xd4af37, metalness: 0.8 }));
    gold.position.set(0, 0, -H / 2 + G / 2);
    group.add(gold);

    const icGeo = new THREE.BoxGeometry(IC.w, IC.h, IC.d);
    const icMat = new THREE.MeshStandardMaterial({ color: 0x111111 });
    for (let rank = 0; rank < 2; rank++) {
      const zOffset = rank === 0 ? (T / 2 + IC.h / 2) : -(T / 2 + IC.h / 2);
      for (let i = 0; i < 8; i++) {
        const icMesh = new THREE.Mesh(icGeo, icMat);
        icMesh.position.set(-L / 2 + (L / 9) * (i + 1), 0, zOffset);
        icMesh.rotation.x = Math.PI / 2;
        group.add(icMesh);
      }
    }
    scene.add(group);

    // 5. ResizeObserver (Gate against zero-dimension WebGL crash)
    const resizeObserver = new ResizeObserver((entries) => {
      for (let entry of entries) {
        const { width, height } = entry.contentRect;
        if (width > 0 && height > 0) {
          camera.aspect = width / height;
          camera.updateProjectionMatrix();
          renderer.setSize(width, height);
        }
      }
    });
    resizeObserver.observe(currentMount);

    // 6. Animation Loop
    let frameId;
    const animate = () => {
      frameId = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    return () => {
      resizeObserver.disconnect();
      cancelAnimationFrame(frameId);
      controls.dispose();
      renderer.dispose();
      if (currentMount.contains(renderer.domElement)) {
        currentMount.removeChild(renderer.domElement);
      }
    };
  }, []);

  return (
    <section style={{ marginTop: '1.5rem' }}>
      <h2 style={{ color: '#111' }}>Parametric 3D CAD Viewer (Client-Side)</h2>
      <div ref={mountRef} style={{ width: '100%', height: '380px', background: '#020617', borderRadius: '8px', overflow: 'hidden' }} />
    </section>
  );
}
