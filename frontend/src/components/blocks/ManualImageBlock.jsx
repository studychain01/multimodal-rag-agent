import { useState, useEffect } from "react"
import { API_BASE } from "../../apiConfig"

export default function ManualImageBlock({ block }) {
  const [imageSrc, setImageSrc] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function loadImage() {
      try {
        // load first page (or only page)
        const page = block.pages?.[0] || block.page
        const source = block.source

        const response = await fetch(
          `${API_BASE}/page/${source}/${page}`
        )
        const data = await response.json()
        setImageSrc(`data:image/png;base64,${data.data}`)
      } catch (error) {
        console.error("Failed to load image:", error)
      }
      setLoading(false)
    }
    loadImage()
  }, [block])

  if (loading) {
    return (
      <div className="border border-gray-700 rounded p-4 
                      animate-pulse bg-gray-900 h-32" />
    )
  }

  if (!imageSrc) return null

  return (
    <div className="border border-gray-700 rounded overflow-hidden">
      <img
        src={imageSrc}
        alt={block.caption}
        className="w-full object-contain bg-white"
      />
      <div className="px-3 py-2 bg-gray-900 border-t border-gray-700">
        <span className="text-xs font-mono text-gray-500">
          📄 {block.caption} — {block.source} p.{block.pages?.[0]}
        </span>
      </div>
    </div>
  )
}