export default function ChatInput({ value, onChange, onSubmit, loading }) {
    function handleKeyDown(e) {
      if (e.key === "Enter" && !e.shiftKey && !loading) {
        e.preventDefault()
        onSubmit(value)
      }
    }
  
    return (
      <div className="flex gap-3">
        <input
          type="text"
          value={value}
          onChange={e => onChange(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about your Vulcan OmniPro 220..."
          disabled={loading}
          className="flex-1 bg-gray-900 border border-gray-700 rounded
                     px-4 py-3 text-sm font-mono text-white
                     placeholder-gray-600
                     focus:outline-none focus:border-orange-500
                     disabled:opacity-50"
        />
        <button
          onClick={() => onSubmit(value)}
          disabled={loading || !value.trim()}
          className="px-4 py-3 bg-orange-500 hover:bg-orange-600
                     disabled:opacity-50 disabled:cursor-not-allowed
                     rounded text-white text-sm font-mono font-bold
                     transition-colors duration-200"
        >
          Send
        </button>
      </div>
    )
  }