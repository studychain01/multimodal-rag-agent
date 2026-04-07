import { useState } from "react"

const DUTY_CYCLES = {
  MIG: {
    "240": [
      { amps: 200, duty: 25, weld: 2.5, rest: 7.5 },
      { amps: 130, duty: 60, weld: 6, rest: 4 },
      { amps: 115, duty: 100, weld: 10, rest: 0 },
    ],
    "120": [
      { amps: 100, duty: 40, weld: 4, rest: 6 },
      { amps: 85, duty: 60, weld: 6, rest: 4 },
      { amps: 75, duty: 100, weld: 10, rest: 0 },
    ]
  },
  TIG: {
    "240": [
      { amps: 175, duty: 30, weld: 3, rest: 7 },
      { amps: 125, duty: 60, weld: 6, rest: 4 },
      { amps: 105, duty: 100, weld: 10, rest: 0 },
    ],
    "120": [
      { amps: 125, duty: 40, weld: 4, rest: 6 },
      { amps: 105, duty: 60, weld: 6, rest: 4 },
      { amps: 90, duty: 100, weld: 10, rest: 0 },
    ]
  },
  Stick: {
    "240": [
      { amps: 175, duty: 25, weld: 2.5, rest: 7.5 },
      { amps: 115, duty: 60, weld: 6, rest: 4 },
      { amps: 100, duty: 100, weld: 10, rest: 0 },
    ],
    "120": [
      { amps: 80, duty: 40, weld: 4, rest: 6 },
      { amps: 70, duty: 60, weld: 6, rest: 4 },
      { amps: 60, duty: 100, weld: 10, rest: 0 },
    ]
  }
}

function calculate(process, voltage, amps) {
  const table = DUTY_CYCLES[process]?.[voltage]
  if (!table) return null

  // find closest bracket at or below requested amps
  const sorted = [...table].sort((a, b) => b.amps - a.amps)
  const bracket = sorted.find(row => amps >= row.amps) || sorted[sorted.length - 1]

  return bracket
}

export default function DutyCycleCalculator({
  defaultProcess = "MIG",
  defaultAmps = 100,
  defaultVoltage = "240"
}) {
  const [process, setProcess] = useState(defaultProcess)
  const [voltage, setVoltage] = useState(defaultVoltage)
  const [amps, setAmps] = useState(defaultAmps)

  const result = calculate(process, voltage, amps)

  return (
    <div className="border border-orange-500/30 rounded bg-gray-900 p-4">
      <div className="text-xs font-mono text-orange-500 uppercase 
                      tracking-widest mb-4">
        Duty Cycle Calculator
      </div>

      <div className="grid grid-cols-3 gap-3 mb-4">
        <div>
          <label className="text-xs font-mono text-gray-500 block mb-1">
            Process
          </label>
          <select
            value={process}
            onChange={e => setProcess(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded
                       px-2 py-1.5 text-sm font-mono text-white
                       focus:outline-none focus:border-orange-500"
          >
            <option>MIG</option>
            <option>TIG</option>
            <option>Stick</option>
          </select>
        </div>

        <div>
          <label className="text-xs font-mono text-gray-500 block mb-1">
            Voltage
          </label>
          <select
            value={voltage}
            onChange={e => setVoltage(e.target.value)}
            className="w-full bg-gray-800 border border-gray-700 rounded
                       px-2 py-1.5 text-sm font-mono text-white
                       focus:outline-none focus:border-orange-500"
          >
            <option value="240">240V</option>
            <option value="120">120V</option>
          </select>
        </div>

        <div>
          <label className="text-xs font-mono text-gray-500 block mb-1">
            Amps
          </label>
          <input
            type="number"
            value={amps}
            onChange={e => setAmps(Number(e.target.value))}
            className="w-full bg-gray-800 border border-gray-700 rounded
                       px-2 py-1.5 text-sm font-mono text-white
                       focus:outline-none focus:border-orange-500"
          />
        </div>
      </div>

      {result && (
        <div className="grid grid-cols-3 gap-3">
          <div className="bg-gray-800 rounded p-3 text-center">
            <div className="text-2xl font-mono font-bold text-orange-500">
              {result.duty}%
            </div>
            <div className="text-xs font-mono text-gray-500 mt-1">
              Duty Cycle
            </div>
          </div>
          <div className="bg-gray-800 rounded p-3 text-center">
            <div className="text-2xl font-mono font-bold text-green-400">
              {result.weld}
            </div>
            <div className="text-xs font-mono text-gray-500 mt-1">
              Min Welding
            </div>
          </div>
          <div className="bg-gray-800 rounded p-3 text-center">
            <div className="text-2xl font-mono font-bold text-red-400">
              {result.rest}
            </div>
            <div className="text-xs font-mono text-gray-500 mt-1">
              Min Resting
            </div>
          </div>
        </div>
      )}
    </div>
  )
}