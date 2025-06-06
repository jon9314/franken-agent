import { UserIcon, CpuChipIcon } from '@heroicons/react/24/solid';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm'; // For GitHub Flavored Markdown (tables, strikethrough, etc.)

const ChatMessage = ({ message }) => {
  const isUser = message.sender === 'user';
  
  return (
    <div className={`flex items-end gap-2.5 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {/* Bot Avatar */}
      {!isUser && (
        <div className="flex-shrink-0 h-8 w-8 sm:h-10 sm:w-10 rounded-full bg-blue-500 text-white flex items-center justify-center shadow">
          <CpuChipIcon className="h-4 w-4 sm:h-5 sm:w-5"/>
        </div>
      )}

      {/* Message Bubble */}
      <div 
        className={`px-3 py-2 sm:px-4 sm:py-3 rounded-xl max-w-[70%] sm:max-w-[75%] shadow-md break-words text-sm sm:text-base ${
          isUser 
            ? 'bg-blue-600 text-white rounded-br-none' 
            : `bg-white text-gray-800 rounded-bl-none ${message.isError ? 'border border-red-300 bg-red-50 !text-red-700' : 'border border-gray-200'}`
        }`}
      >
        {/* Use ReactMarkdown for bot messages to render formatting like code blocks, lists, etc. */}
        {isUser ? (
          <p className="whitespace-pre-wrap">{message.text}</p> // Preserve user's whitespace
        ) : (
          <div className="prose prose-sm max-w-none"> 
            {/* `prose` class from @tailwindcss/typography can improve markdown rendering */}
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                // Customize rendering of Markdown elements if needed
                p: ({node, ...props}) => <p className="mb-2 last:mb-0" {...props} />,
                ol: ({node, ...props}) => <ol className="list-decimal list-inside my-2 pl-4" {...props} />,
                ul: ({node, ...props}) => <ul className="list-disc list-inside my-2 pl-4" {...props} />,
                li: ({node, ...props}) => <li className="mb-1" {...props} />,
                code: ({node, inline, className, children, ...props}) => {
                  const match = /language-(\w+)/.exec(className || '');
                  return !inline && match ? (
                    <pre className="bg-gray-800 text-gray-100 p-3 rounded-md overflow-x-auto my-2 text-xs sm:text-sm font-mono">
                      <code className={`language-${match[1]}`} {...props}>{children}</code>
                    </pre>
                  ) : (
                    <code className="bg-gray-200 text-red-600 px-1 py-0.5 rounded text-xs sm:text-sm font-mono" {...props}>
                      {children}
                    </code>
                  );
                },
                table: ({node, ...props}) => <table className="table-auto border-collapse border border-gray-300 my-2 w-full text-xs sm:text-sm" {...props} />,
                thead: ({node, ...props}) => <thead className="bg-gray-100" {...props} />,
                th: ({node, ...props}) => <th className="border border-gray-300 px-2 py-1 text-left font-semibold" {...props} />,
                td: ({node, ...props}) => <td className="border border-gray-300 px-2 py-1" {...props} />,
                a: ({node, ...props}) => <a className="text-blue-600 hover:underline" {...props} />,
              }}
            >
              {message.text}
            </ReactMarkdown>
          </div>
        )}
        {!isUser && message.modelUsed && !message.isError && (
          <p className="text-xs text-gray-400 mt-1.5 text-right italic">via: {message.modelUsed}</p>
        )}
      </div>

      {/* User Avatar */}
       {isUser && (
        <div className="flex-shrink-0 h-8 w-8 sm:h-10 sm:w-10 rounded-full bg-slate-200 text-slate-600 flex items-center justify-center shadow">
          <UserIcon className="h-4 w-4 sm:h-5 sm:w-5"/>
        </div>
      )}
    </div>
  );
};

export default ChatMessage;