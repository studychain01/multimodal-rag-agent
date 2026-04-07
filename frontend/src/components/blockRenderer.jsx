import ManualImageBlock from "./blocks/ManualImageBlock"
import SVGBlock from "./blocks/SVGBlock"
import MermaidBlock from "./blocks/MermaidBlock"
import DutyCycleCalculator from "./interactive/DutyCycleCalculator"
import WireSettingsConfigurator from "./interactive/WireSettingsConfigurator"
import PolarityDiagram from "./interactive/PolarityDiagram"

const COMPONENTS = {
  DutyCycleCalculator,
  WireSettingsConfigurator,
  PolarityDiagram,
}

export default function BlockRenderer({ block }) {
  switch (block.type) {

    case "text":
      return (
        <div className="text-sm font-mono text-gray-200 leading-relaxed
                        whitespace-pre-wrap">
          {block.content}
        </div>
      )

    case "manual_image":
      return <ManualImageBlock block={block} />

    case "svg":
      return <SVGBlock block={block} />

    case "mermaid":
      return <MermaidBlock block={block} />

    case "component":
      const Component = COMPONENTS[block.name]
      if (!Component) return null
      return <Component {...block.props} />

    default:
      return null
  }
}