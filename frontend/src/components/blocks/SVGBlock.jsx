export default function SVGBlock({ block }) {
    return (
      <div
        className="border border-gray-700 rounded p-4 bg-gray-900
                   flex justify-center"
        dangerouslySetInnerHTML={{ __html: block.markup }}
      />
    )
  }