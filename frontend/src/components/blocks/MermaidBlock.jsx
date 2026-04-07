import { useEffect, useRef } from "react"
import mermaid from "mermaid"

mermaid.initialize({
  startOnLoad: false,
  theme: "dark",
  themeVariables: {
    primaryColor: "#f97316",
    primaryTextColor: "#fff",
    primaryBorderColor: "#f97316",
    lineColor: "#6b7280",
    background: "#111827",
  }
})

export default function MermaidBlock({ block }) {
  const ref = useRef(null)

  useEffect(() => {
    if (!ref.current) return

    const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`

    mermaid.render(id, block.diagram).then(({ svg }) => {
      if (ref.current) {
        ref.current.innerHTML = svg
      }
    }).catch(console.error)
  }, [block.diagram])

  return (
    <div
      ref={ref}
      className="border border-gray-700 rounded p-4 bg-gray-900
                 flex justify-center overflow-x-auto"
    />
  )
}