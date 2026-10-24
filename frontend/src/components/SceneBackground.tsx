import { useMemo, useRef } from "react";
import { Canvas, useFrame, useThree } from "@react-three/fiber";
import { Float, Icosahedron, Octahedron, TorusKnot } from "@react-three/drei";
import * as THREE from "three";
import LogoMark from "./LogoMark";

/* Warm "Cream Ink" palette, lifted into 3D. */
const ACCENT = "#b4541c";
const ACCENT_2 = "#c9702f";
const GREEN = "#6f7c2f";
const CREAM = "#f0e5d4";

/* A drifting field of warm motes, parallaxed by the pointer. */
function Motes({ count = 320 }: { count?: number }) {
  const ref = useRef<THREE.Points>(null);

  const [positions, colors] = useMemo(() => {
    const pos = new Float32Array(count * 3);
    const col = new Float32Array(count * 3);
    const palette = [ACCENT, ACCENT_2, GREEN, CREAM].map((c) => new THREE.Color(c));
    for (let i = 0; i < count; i++) {
      pos[i * 3 + 0] = (Math.random() - 0.5) * 22;
      pos[i * 3 + 1] = (Math.random() - 0.5) * 14;
      pos[i * 3 + 2] = (Math.random() - 0.5) * 12 - 2;
      const c = palette[(Math.random() * palette.length) | 0];
      col[i * 3 + 0] = c.r;
      col[i * 3 + 1] = c.g;
      col[i * 3 + 2] = c.b;
    }
    return [pos, col];
  }, [count]);

  useFrame((state, delta) => {
    if (!ref.current) return;
    ref.current.rotation.y += delta * 0.02;
    const { x, y } = state.pointer;
    ref.current.rotation.x = THREE.MathUtils.lerp(ref.current.rotation.x, y * 0.12, 0.04);
    ref.current.position.x = THREE.MathUtils.lerp(ref.current.position.x, x * 0.6, 0.04);
  });

  return (
    <points ref={ref}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-color" args={[colors, 3]} />
      </bufferGeometry>
      <pointsMaterial
        size={0.07}
        vertexColors
        transparent
        opacity={0.75}
        depthWrite={false}
        sizeAttenuation
        blending={THREE.AdditiveBlending}
      />
    </points>
  );
}

/* A few slow-floating low-poly solids with a soft matte finish. */
function Solids() {
  const mat = (color: string, opacity = 1) => (
    <meshStandardMaterial
      color={color}
      roughness={0.35}
      metalness={0.15}
      flatShading
      transparent={opacity < 1}
      opacity={opacity}
    />
  );
  return (
    <>
      <Float speed={1.1} rotationIntensity={0.9} floatIntensity={1.2}>
        <Icosahedron args={[1.35, 0]} position={[-7.6, 2.4, -5]}>
          {mat(ACCENT)}
        </Icosahedron>
      </Float>
      <Float speed={0.8} rotationIntensity={1.2} floatIntensity={1.0}>
        <Octahedron args={[1.0, 0]} position={[7.8, -2.2, -4]}>
          {mat(GREEN)}
        </Octahedron>
      </Float>
      <Float speed={1.4} rotationIntensity={0.6} floatIntensity={1.4}>
        <TorusKnot args={[0.5, 0.18, 120, 16]} position={[7.2, 3.0, -6]}>
          {mat(ACCENT_2)}
        </TorusKnot>
      </Float>
      <Float speed={0.9} rotationIntensity={1.4} floatIntensity={0.9}>
        <Icosahedron args={[0.7, 0]} position={[-7.0, -3.0, -4.5]}>
          {mat(ACCENT_2, 0.85)}
        </Icosahedron>
      </Float>
    </>
  );
}

/* Gentle dolly so the scene breathes without the user touching anything. */
function Breathe() {
  const { camera } = useThree();
  useFrame((state) => {
    const t = state.clock.elapsedTime;
    camera.position.z = 9 + Math.sin(t * 0.25) * 0.4;
    camera.lookAt(0, 0, 0);
  });
  return null;
}

export default function SceneBackground() {
  return (
    <div className="scene-bg" aria-hidden>
      <Canvas
        dpr={[1, 1.5]}
        camera={{ position: [0, 0, 9], fov: 55 }}
        gl={{ antialias: true, alpha: true }}
      >
        <ambientLight intensity={0.9} />
        <directionalLight position={[5, 6, 4]} intensity={1.1} color={CREAM} />
        <directionalLight position={[-6, -3, 2]} intensity={0.5} color={ACCENT} />
        <Breathe />
        <Motes />
        <LogoMark position={[0, 0.9, -5]} scale={1.25} speed={0.8} phase={0} drift={0.7} />
        <LogoMark position={[-5.2, 2.1, -7]} scale={0.6} speed={1.1} phase={1.6} drift={1.2} />
        <LogoMark position={[5.8, -1.4, -6.2]} scale={0.85} speed={0.9} phase={3.1} drift={1.0} />
        <LogoMark position={[-6, -2.6, -8.5]} scale={0.45} speed={1.3} phase={4.4} drift={1.4} />
        <LogoMark position={[4.6, 3.1, -9]} scale={0.5} speed={0.7} phase={2.2} drift={1.1} />
      </Canvas>
    </div>
  );
}
