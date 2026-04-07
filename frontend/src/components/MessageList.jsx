import Message from "./Message"

export default function MessageList({ messages }) {
  return (
    <div className="flex flex-col gap-6">
      {messages.map((message, i) => (
        <Message key={i} message={message} />
      ))}
    </div>
  )
}