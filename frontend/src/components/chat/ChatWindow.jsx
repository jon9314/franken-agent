import { useEffect, useRef } from 'react';
import ChatMessage from './ChatMessage'; // Ensure path is correct

const ChatWindow = ({ messages }) => {
  const messagesEndRef = useRef(null); // Ref for the bottom of the messages list

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  // Scroll to bottom whenever the messages array updates
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  return (
    <div className="flex-1 p-4 sm:p-6 overflow-y-auto space-y-4 bg-slate-50">
      {messages.map((msg) => ( // Use msg.id if available and unique, otherwise index
        <ChatMessage key={msg.id || Math.random()} message={msg} /> // Ensure unique key
      ))}
      <div ref={messagesEndRef} /> {/* Invisible element to help scroll to bottom */}
    </div>
  );
};

export default ChatWindow;