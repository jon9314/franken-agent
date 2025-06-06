import { useState, useRef, useEffect } from 'react';
import { PaperAirplaneIcon } from '@heroicons/react/24/solid';

const ChatInput = ({ onSendMessage, isLoading }) => {
  const [prompt, setPrompt] = useState('');
  const textareaRef = useRef(null);

  // Auto-resize textarea based on content
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'; // Reset height
      textareaRef.current.style.height = `${textareaRef.current.scrollHeight}px`; // Set to scroll height
    }
  }, [prompt]);

  const handleSubmit = (e) => {
    e.preventDefault(); // Prevent default form submission
    if (prompt.trim() && !isLoading) {
      onSendMessage(prompt.trim());
      setPrompt(''); // Clear input after sending
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !isLoading) { // Send on Enter (if not Shift+Enter)
        e.preventDefault(); // Prevent newline in textarea on Enter
        handleSubmit(e);    // Submit form
    }
    // Allow Shift+Enter for newline
  };

  return (
    <form onSubmit={handleSubmit} className="p-3 sm:p-4 bg-slate-100 border-t border-gray-200">
      <div className="flex items-end space-x-2 sm:space-x-3">
        <textarea
          ref={textareaRef}
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask Frankie anything..."
          className="flex-1 px-3 py-2.5 border border-gray-300 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none text-sm sm:text-base leading-relaxed"
          rows="1" // Start with one row, will expand due to useEffect
          disabled={isLoading}
          style={{ minHeight: '48px', maxHeight: '200px' }} // Control min/max height
        />
        <button
          type="submit"
          className="bg-blue-600 text-white p-2.5 sm:p-3 rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 flex items-center justify-center shadow-sm disabled:bg-blue-300 disabled:cursor-not-allowed transition-colors"
          disabled={isLoading || !prompt.trim()}
          aria-label="Send message"
        >
          <PaperAirplaneIcon className="h-5 w-5 sm:h-6 sm:w-6" />
        </button>
      </div>
    </form>
  );
};

export default ChatInput;