import { useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import { Float } from "@react-three/drei";
import * as THREE from "three";

/* Left banner half, traced from the reference emblem:
   - slanted top edge that rises toward the centre,
   - a thin vertical slit top & bottom where the two halves nearly meet,
   - the inner edge flaring out to form the left side of the central rounded "O",
   - rounded outer-left corners.
   The right half is this mirrored on X. */
function leftHalf(): THREE.Shape {
  const s = new THREE.Shape();
  s.moveTo(-1.94, 0.55); // A: outer top-left corner
  s.quadraticCurveTo(-1.0, 0.7, -0.14, 0.64); // top edge, gently rising to inner-top
  s.lineTo(-0.14, 0.47); // thin top slit straight down
  s.quadraticCurveTo(-0.58, 0.47, -0.59, 0.3); // "O" top-left rounded corner
  s.lineTo(-0.59, -0.3); // "O" left side (vertical)
  s.quadraticCurveTo(-0.58, -0.47, -0.14, -0.47); // "O" bottom-left rounded corner
  s.lineTo(-0.14, -0.65); // thin bottom slit down to inner-bottom
  s.quadraticCurveTo(-1.0, -0.72, -1.94, -0.64); // bottom edge back to outer-bottom-left
  s.bezierCurveTo(-2.06, -0.3, -2.06, 0.3, -1.94, 0.55); // rounded outer-left edge
  return s;
}

function rightHalf(): THREE.Shape {
  const s = new THREE.Shape();
  s.moveTo(1.94, 0.55);
  s.quadraticCurveTo(1.0, 0.7, 0.14, 0.64);
  s.lineTo(0.14, 0.47);
  s.quadraticCurveTo(0.58, 0.47, 0.59, 0.3);
  s.lineTo(0.59, -0.3);
  s.quadraticCurveTo(0.58, -0.47, 0.14, -0.47);
  s.lineTo(0.14, -0.65);
  s.quadraticCurveTo(1.0, -0.72, 1.94, -0.64);
  s.bezierCurveTo(2.06, -0.3, 2.06, 0.3, 1.94, 0.55);
  return s;
}

const EXTRUDE: THREE.ExtrudeGeometryOptions = {
  depth: 0.34,
  bevelEnabled: true,
  bevelThickness: 0.06,
  bevelSize: 0.05,
  bevelSegments: 3,
  curveSegments: 32,
};

export default function LogoMark(props: {
  position?: [number, number, number];
  scale?: number;
  color?: string;
  speed?: number;
  phase?: number;
  drift?: number;
}) {
  const {
    position = [0, 0, -4],
    scale = 1,
    color = "#241812",
    speed = 1,
    phase = 0,
    drift = 1,
  } = props;
  const grp = useRef<THREE.Group>(null);
  const [bx, by, bz] = position;

  const geoms = useMemo(() => {
    const left = new THREE.ExtrudeGeometry(leftHalf(), EXTRUDE);
    const right = new THREE.ExtrudeGeometry(rightHalf(), EXTRUDE);
    // centre the depth on z = 0 so it rotates about its own middle
    left.translate(0, 0, -EXTRUDE.depth! / 2);
    right.translate(0, 0, -EXTRUDE.depth! / 2);
    return { left, right };
  }, []);

  // each emblem drifts along its own slow elliptical path and turns gently
  useFrame((state) => {
    if (!grp.current) return;
    const t = state.clock.elapsedTime * speed + phase;
    grp.current.position.x = bx + Math.sin(t * 0.3) * drift;
    grp.current.position.y = by + Math.cos(t * 0.23) * drift * 0.6;
    grp.current.position.z = bz + Math.sin(t * 0.17) * drift * 0.4;
    grp.current.rotation.y = Math.sin(t * 0.2) * 0.35;
    grp.current.rotation.z = Math.sin(t * 0.14) * 0.1;
  });

  return (
    <Float speed={0.8} rotationIntensity={0} floatIntensity={0.4}>
      <group ref={grp} position={position} scale={scale}>
        <mesh geometry={geoms.left}>
          <meshStandardMaterial color={color} roughness={0.28} metalness={0.65} />
        </mesh>
        <mesh geometry={geoms.right}>
          <meshStandardMaterial color={color} roughness={0.28} metalness={0.65} />
        </mesh>
      </group>
    </Float>
  );
}
