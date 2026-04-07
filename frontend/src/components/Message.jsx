import BlockRenderer from "./BlockRenderer"

export default function Message({ message }) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-lg bg-gray-800 rounded px-4 py-3
                        text-sm font-mono text-white">
          {message.content}
        </div>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-center gap-2">
        <div className="w-1.5 h-1.5 rounded-full bg-orange-500"></div>
        <span className="text-xs font-mono text-orange-500 uppercase tracking-widest">
          OmniPro Agent
        </span>
      </div>
      <div className="flex flex-col gap-4">
        {message.blocks?.map((block, i) => (
          <BlockRenderer key={i} block={block} />
        ))}
      </div>
    </div>
  )
}