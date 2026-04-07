import { useState } from "react"

const SETTINGS = {
  "Mild Steel": {
    "MIG": {
      "24Ga": { wfs: "100-150", voltage: "13-15V", wire: "0.025\"", gas: "C25" },
      "22Ga": { wfs: "120-170", voltage: "14-16V", wire: "0.025\"", gas: "C25" },
      "18Ga": { wfs: "150-200", voltage: "15-17V", wire: "0.030\"", gas: "C25" },
      "16Ga": { wfs: "175-225", voltage: "16-18V", wire: "0.030\"", gas: "C25" },
      "1/8\"": { wfs: "200-280", voltage: "17-20V", wire: "0.035\"", gas: "C25" },
      "3/16\"": { wfs: "250-350", voltage: "19-22V", wire: "0.035\"", gas: "C25" },
    },
    "Flux-Cored": {
      "18Ga": { wfs: "150-200", voltage: "15-17V", wire: "0.030\"", gas: "None" },
      "16Ga": { wfs: "175-225", voltage: "16-18V", wire: "0.035\"", gas: "None" },
      "1/8\"": { wfs: "200-280", voltage: "18-21V", wire: "0.035\"", gas: "None" },
      "3/16\"": { wfs: "250-350", voltage: "20-23V", wire: "0.045\"", gas: "None" },
      "5/16\"": { wfs: "300-400", voltage: "22-25V", wire: "0.045\"", gas: "None" },
    }
  },
  "Stainless Steel": {
    "MIG": {
      "24Ga": { wfs: "100-140", voltage: "13-15V", wire: "0.025\"", gas: "Tri-Mix" },
      "18Ga": { wfs: "140-190", voltage: "15-17V", wire: "0.030\"", gas: "Tri-Mix" },
      "1/8\"": { wfs: "190-250", voltage: "17-20V", wire: "0.035\"", gas: "Tri-Mix" },
    }
  }
}

export default function WireSettingsConfigurator({
  defaultMaterial = "Mild Steel",
  defaultProcess = "MIG",
  defaultThickness = "1/8\""
}) {
  const [material, setMaterial] = useState(defaultMaterial)
  const [process, setProcess] = useState(defaultProcess)
  const [thickness, setThickness] = useState(defaultThickness)

  const materials = Object.keys(SETTINGS)
  const processes = Object.keys(SETTINGS[material] || {})
  const thicknesses = Object.keys(SETTINGS[material]?.[process] || {})
  const settings = SETTINGS[material]?.[process]?.[thickness]

  return (
    <div className="border border-orange-500/30 rounded bg-gray-900 p-4">
      <div className="text-xs font-mono text-orange-500 uppercase
                      tracking-widest mb-4">
        Wire Settings Configurator
      </div>

      <div className="grid grid-cols-3 gap-3 mb-4">
        <div>
          <label className="text-xs font-mono text-gray-500 block mb-1">
            Material
          </label>
          <select
            value={material}
            onChange={e => {
              setMaterial(e.target.value)
              setProcess(Object.keys(SETTINGS[e.target.value])[0])
              setThickness("")
            }}
            className="w-full bg-gray-800 border border-gray-700 rounded
                       px-2 py-1.5 text-sm font-mono text-white
                       focus:outline-none focus:border-orange-500"
          >
            {materials.map(m => <option key={m}>{m}</option>)}
          </select>
        </div>

        <div>
          <label className="text-xs font-mono text-gray-500 block mb-1">
            Process
          </label>
          <select
            value={process}
            onChange={e => {
              setProcess(e.target.value)
              setThickness("")
            }}
            className="w-full bg-gray-800 border border-gray-700 rounded
                       px-2 py-1.5 text-sm font-mono text-white
                       focus:outline-none focus:border-orange-500"
          >
            {processes.map(p => <option key={p}>{p}</option>)}
          </select>
        </div>

        <div>
          <label className="text-xs font-mono text-gray-500 block mb-1">
            Thickness
          </label>
          <select
            value={thickness}
            onChange={e => setThickness(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded
                       px-2 py-1.5 text-sm font-mono text-white
                       focus:outline-none focus:border-orange-500"
          >
            <option value="">Select...</option>
            {thicknesses.map(t => <option key={t}>{t}</option>)}
          </select>
        </div>
      </div>

      {settings ? (
        <div className="grid grid-cols-2 gap-2">
          <div className="bg-gray-800 rounded p-3">
            <div className="text-xs font-mono text-gray-500 mb-1">
              Wire Feed Speed
            </div>
            <div className="text-lg font-mono font-bold text-orange-500">
              {settings.wfs} IPM
            </div>
          </div>
          <div className="bg-gray-800 rounded p-3">
            <div className="text-xs font-mono text-gray-500 mb-1">
              Voltage
            </div>
            <div className="text-lg font-mono font-bold text-orange-500">
              {settings.voltage}
            </div>
          </div>
          <div className="bg-gray-800 rounded p-3">
            <div className="text-xs font-mono text-gray-500 mb-1">
              Wire Diameter
            </div>
            <div className="text-lg font-mono font-bold text-white">
              {settings.wire}
            </div>
          </div>
          <div className="bg-gray-800 rounded p-3">
            <div className="text-xs font-mono text-gray-500 mb-1">
              Shielding Gas
            </div>
            <div className="text-lg font-mono font-bold text-white">
              {settings.gas}
            </div>
          </div>
        </div>
      ) : (
        <div className="text-center text-gray-600 text-sm font-mono py-4">
          Select material, process, and thickness
        </div>
      )}
    </div>
  )
}