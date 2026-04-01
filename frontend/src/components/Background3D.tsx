import { useRef, useMemo } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Points, PointMaterial } from '@react-three/drei'
// @ts-ignore
import * as random from 'maath/random/dist/maath-random.esm'

function Swarm() {
  const ref = useRef<any>(null)
  
  // Generate slightly larger sphere of 2500 points for a "cyber" look
  const sphere = useMemo(() => random.inSphere(new Float32Array(2500 * 3), { radius: 1.5 }), [])

  // Slowly rotate the entire swarm
  useFrame((_state, delta) => {
    if (ref.current) {
      ref.current.rotation.x -= delta / 15
      ref.current.rotation.y -= delta / 20
    }
  })

  return (
    <group rotation={[0, 0, Math.PI / 4]}>
      <Points ref={ref} positions={sphere as Float32Array} stride={3} frustumCulled={false}>
        <PointMaterial
          transparent
          color="#818cf8"
          size={0.008}
          sizeAttenuation={true}
          depthWrite={false}
          blending={2} // Additive blending for that glowing cyber aesthetic
        />
      </Points>
    </group>
  )
}

export default function Background3D() {
  return (
    <div className="fixed inset-0 z-0 pointer-events-none opacity-60">
      <Canvas camera={{ position: [0, 0, 1] }}>
        <Swarm />
      </Canvas>
    </div>
  )
}
