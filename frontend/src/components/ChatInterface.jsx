import { useState, useRef, useEffect } from "react"
import MessageList from "./MessageList"
import ChatInput from "./ChatInput"
import SuggestedQuestions from "./SuggestedQuestions.jsx"

const SUGGESTED = [
  "What's the duty cycle for MIG welding at 200A on 240V?",
  "I'm getting porosity in my flux-cored welds. What should I check?",
  "What polarity setup do I need for TIG welding?",
]

export default function ChatInterface() {
  const [messages, setMessages] = useState([])
  const [sessionId, setSessionId] = useState(null)
  const [loading, setLoading] = useState(false)
  const [input, setInput] = useState("")
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, loading])

  async function sendMessage(userInput) {
    if (!userInput.trim()) return

    const userMessage = { role: "user", content: userInput }
    setMessages(prev => [...prev, userMessage])
    setInput("")
    setLoading(true)

    try {
      const response = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: userInput,
          session_id: sessionId,
        })
      })

      const data = await response.json()

      if (data.session_id) setSessionId(data.session_id)

      const agentMessage = {
        role: "agent",
        blocks: data.blocks
      }

      setMessages(prev => [...prev, agentMessage])

    } catch (error) {
      setMessages(prev => [...prev, {
        role: "agent",
        blocks: [{
          type: "text",
          content: "Something went wrong. Please try again."
        }]
      }])
    }

    setLoading(false)
  }

  return (
    <div className="flex flex-col h-screen max-w-4xl mx-auto">

      {/* header */}
      <div className="border-b border-gray-800 px-6 py-4">
        <div className="flex items-center gap-3">
          <div className="w-2 h-2 rounded-full bg-orange-500"></div>
          <h1 className="text-sm font-mono font-bold tracking-widest uppercase text-orange-500">
            Vulcan OmniPro 220
          </h1>
          <span className="text-gray-600 text-xs font-mono">
            Technical Support
          </span>
        </div>
      </div>

      {/* messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {messages.length === 0 && (
          <SuggestedQuestions
            questions={SUGGESTED}
            onSelect={sendMessage}
          />
        )}
        <MessageList messages={messages} />
        {loading && (
          <div className="flex gap-2 mt-4">
            <div className="w-2 h-2 rounded-full bg-orange-500 animate-bounce"></div>
            <div className="w-2 h-2 rounded-full bg-orange-500 animate-bounce delay-100"></div>
            <div className="w-2 h-2 rounded-full bg-orange-500 animate-bounce delay-200"></div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* input */}
      <div className="border-t border-gray-800 px-6 py-4">
        <ChatInput
          value={input}
          onChange={setInput}
          onSubmit={sendMessage}
          loading={loading}
        />
      </div>

    </div>
  )
}