import { useRef } from 'react'
import { Canvas, useFrame } from '@react-three/fiber'
import { Icosahedron } from '@react-three/drei'

function WireframeGlobe() {
  const ref = useRef<any>(null)

  // Slowly rotate the wireframe geometry
  useFrame((_state, delta) => {
    if (ref.current) {
      ref.current.rotation.y += delta * 0.1
      ref.current.rotation.x += delta * 0.05
    }
  })

  return (
    <group rotation={[0, 0, Math.PI / 16]}>
      {/* 
        A highly detailed icosahedron acting as a holographic globe/radar.
        args: [radius, detail]
      */}
      <Icosahedron ref={ref} args={[1.8, 3]}>
        <meshBasicMaterial 
          color="#00ddff" 
          wireframe={true} 
          transparent 
          opacity={0.15} 
        />
      </Icosahedron>
      
      {/* Inner solid core just to give it depth so the back lines get obscured */}
      <Icosahedron args={[1.78, 3]}>
        <meshBasicMaterial 
          color="#000000" 
        />
      </Icosahedron>
    </group>
  )
}

export default function Background3D() {
  return (
    <div className="fixed inset-0 z-0 pointer-events-none opacity-40">
      <Canvas camera={{ position: [0, 0, 3] }}>
        <WireframeGlobe />
      </Canvas>
    </div>
  )
}
