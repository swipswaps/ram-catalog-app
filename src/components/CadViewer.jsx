import React, { useEffect, useRef } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

export default function CadViewer({ formFactor = 'DIMM', moduleType = 'DDR4' }) {
  const mountRef = useRef(null);

  useEffect(() => {
    if (!mountRef.current) return;
    const currentMount = mountRef.current;

    // 1. Scene Setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x020617);

    // 2. Camera & Renderer
    const camera = new THREE.PerspectiveCamera(45, currentMount.clientWidth / currentMount.clientHeight, 0.1, 1000);
    camera.position.set(160, 90, 160);

    const renderer = new THREE.WebGLRenderer({ antialias: true });
    renderer.setSize(currentMount.clientWidth, currentMount.clientHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    currentMount.appendChild(renderer.domElement);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;

    // 3. Lighting
    scene.add(new THREE.AmbientLight(0xffffff, 0.8));
    const dirLight = new THREE.DirectionalLight(0xffffff, 1.2);
    dirLight.position.set(5, 10, 7);
    scene.add(dirLight);

    // 4. Geometry Generation
    const isSodimm = formFactor === 'SODIMM';
    const L = isSodimm ? 67.6 : 133.35;
    const H = isSodimm ? 30.0 : 31.25;
    const T = isSodimm ? 1.0 : 1.57;
    const G = isSodimm ? 4.0 : 5.0;
    const IC = isSodimm ? { w: 8, h: 1, d: 8 } : { w: 11, h: 1.2, d: 9 };

    const group = new THREE.Group();

    // PCB Base
    const pcbGeo = new THREE.BoxGeometry(L, T, H);
    const pcbMat = new THREE.MeshStandardMaterial({ color: 0x0a5c36, roughness: 0.8 });
    const pcbMesh = new THREE.Mesh(pcbGeo, pcbMat);
    group.add(pcbMesh);

    // Gold Fingers
    const goldGeo = new THREE.BoxGeometry(L, T + 0.02, G);
    const goldMat = new THREE.MeshStandardMaterial({ color: 0xd4af37, metalness: 0.8, roughness: 0.2 });
    const goldMesh = new THREE.Mesh(goldGeo, goldMat);
    goldMesh.position.set(0, 0, -H / 2 + G / 2);
    group.add(goldMesh);

    // IC Packages
    const icGeo = new THREE.BoxGeometry(IC.w, IC.h, IC.d);
    const icMat = new THREE.MeshStandardMaterial({ color: 0x111111, roughness: 0.9 });
    const spacing = L / 9;
    for (let rank = 0; rank < 2; rank++) {
      const zOffset = rank === 0 ? (T / 2 + IC.h / 2) : -(T / 2 + IC.h / 2);
      for (let i = 0; i < 8; i++) {
        const icMesh = new THREE.Mesh(icGeo, icMat);
        icMesh.position.set(-L / 2 + spacing * (i + 1), 0, zOffset);
        icMesh.rotation.x = Math.PI / 2;
        group.add(icMesh);
      }
    }

    scene.add(group);

    // 5. Animation Loop
    let frameId;
    const animate = () => {
      frameId = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    // 6. Resize Handler
    const handleResize = () => {
      if (!currentMount) return;
      camera.aspect = currentMount.clientWidth / currentMount.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(currentMount.clientWidth, currentMount.clientHeight);
    };
    window.addEventListener('resize', handleResize);

    return () => {
      cancelAnimationFrame(frameId);
      window.removeEventListener('resize', handleResize);
      controls.dispose();
      renderer.dispose();
      if (currentMount.contains(renderer.domElement)) {
        currentMount.removeChild(renderer.domElement);
      }
    };
  }, [formFactor, moduleType]);

  return (
    <section style={{ marginTop: '1.5rem' }}>
      <h2 style={{ color: '#111' }}>Parametric 3D CAD Viewer (Client-Side)</h2>
      <div
        ref={mountRef}
        className="cad-container"
        style={{ width: '100%', height: '380px', background: '#020617', borderRadius: '8px', overflow: 'hidden' }}
      />
    </section>
  );
}
