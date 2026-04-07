export default function SuggestedQuestions({ questions, onSelect }) {
  if (!questions?.length) return null

  return (
    <div className="mb-6">
      <p className="text-gray-500 text-xs font-mono uppercase tracking-widest mb-3">
        Try asking
      </p>
      <ul className="flex flex-col gap-2">
        {questions.map((q) => (
          <li key={q}>
            <button
              type="button"
              onClick={() => onSelect(q)}
              className="w-full text-left px-4 py-3 rounded border border-gray-800
                         bg-gray-900/50 hover:border-orange-500/60 hover:bg-gray-900
                         text-sm font-mono text-gray-300 transition-colors duration-200"
            >
              {q}
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}
