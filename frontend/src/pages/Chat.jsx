import { useState, useEffect, useRef, useCallback } from 'react';
import ChatWindow from '@/components/chat/ChatWindow';
import ChatInput from '@/components/chat/ChatInput';
import apiClient from '@/api/index.js';
import useAuth from '@/hooks/useAuth';
import { ListBulletIcon, ArrowPathIcon } from '@heroicons/react/24/outline';

const Chat = () => {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false); // For LLM response loading
  const [error, setError] = useState('');
  const { auth } = useAuth(); // Get auth state, particularly user info for greeting

  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [isLoadingModels, setIsLoadingModels] = useState(true);

  const fetchModels = useCallback(async () => {
    setIsLoadingModels(true);
    setError('');
    try {
      const response = await apiClient.get('/models/'); // API endpoint to list models
      setModels(response.data);
      if (response.data && response.data.length > 0) {
        // Default to the first model in the list, preferring 'local' if available
        const localModel = response.data.find(m => m.server_name === 'local');
        if (localModel) {
            setSelectedModel(`${localModel.server_name}/${localModel.model_name}`);
        } else {
            setSelectedModel(`${response.data[0].server_name}/${response.data[0].model_name}`);
        }
      } else {
        setError("No AI models are currently available. Please check the backend configuration.");
      }
    } catch (err) {
      console.error("Failed to fetch models:", err);
      setError("Could not load available AI models. The backend might be down or misconfigured.");
    } finally {
      setIsLoadingModels(false);
    }
  }, []);

  useEffect(() => {
    fetchModels();
  }, [fetchModels]);

  // Set initial greeting message once user data is available
  useEffect(() => {
    if (auth.user && !auth.isLoading) { // Ensure user is loaded
      setMessages([
        { 
          id: Date.now(), // Simple unique ID for key prop
          sender: 'bot', 
          text: `Hello, ${auth.user.full_name || auth.user.email}! I'm Frankie. How can I assist you today?` 
        }
      ]);
    }
  }, [auth.user, auth.isLoading]);

  const handleSendMessage = async (promptText) => {
    if (!promptText.trim()) return;
    if (!selectedModel && models.length > 0) {
        setError("Please select an AI model first.");
        return;
    }
    if (models.length === 0 && !isLoadingModels) {
        setError("No AI models available to process your request.");
        return;
    }


    const userMessage = { id: Date.now(), sender: 'user', text: promptText };
    setMessages(prevMessages => [...prevMessages, userMessage]);
    setIsLoading(true); // For LLM response
    setError('');

    try {
      const response = await apiClient.post('/chat/', { 
        prompt: promptText,
        model: selectedModel // Send the selected model (e.g., "local/llama3")
      });
      const botMessage = { 
        id: Date.now() + 1, 
        sender: 'bot', 
        text: response.data.response, 
        modelUsed: response.data.model_used 
      };
      setMessages(prevMessages => [...prevMessages, botMessage]);
    } catch (err) {
      const apiError = err.response?.data?.detail || 'Sorry, I encountered an error trying to respond.';
      console.error("Chat send error:", err);
      setError(apiError);
      setMessages(prevMessages => [...prevMessages, {id: Date.now() + 1, sender: 'bot', text: apiError, isError: true}]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)] max-w-5xl mx-auto bg-white shadow-2xl rounded-lg border border-gray-200 overflow-hidden">
      <header className="bg-slate-50 p-3 sm:p-4 border-b border-gray-200 flex flex-col sm:flex-row justify-between items-center gap-2 sm:gap-4">
        <h1 className="text-lg sm:text-xl font-semibold text-gray-800">Frankie AI Chat</h1>
        <div className="flex items-center gap-2">
            {isLoadingModels ? (
                <span className="text-xs text-gray-500 flex items-center"><ArrowPathIcon className="h-4 w-4 animate-spin mr-1"/>Loading models...</span>
            ) : models.length > 0 && (
              <>
                <ListBulletIcon className="h-5 w-5 text-gray-400" title="Select Model" />
                <select 
                  value={selectedModel} 
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="text-xs block w-full max-w-[200px] sm:max-w-xs pl-2 pr-7 py-1.5 border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 rounded-md shadow-sm"
                  disabled={isLoadingModels}
                >
                  {models.map(model => (
                    <option key={`${model.server_name}/${model.model_name}`} value={`${model.server_name}/${model.model_name}`}>
                      {model.model_name} ({model.server_name})
                    </option>
                  ))}
                </select>
              </>
            )}
        </div>
      </header>
      
      <ChatWindow messages={messages} />
      
      <ChatInput onSendMessage={handleSendMessage} isLoading={isLoading} />
      
      {error && !isLoading && (
        <div className="p-2 text-center text-red-600 text-xs bg-red-50 border-t border-red-200">
            Error: {error}
        </div>
      )}
       {models.length === 0 && !isLoadingModels && !error.includes("AI models") && (
         <div className="p-2 text-center text-yellow-700 text-xs bg-yellow-50 border-t border-yellow-200">
            No AI models seem to be configured or available. Please check the Ollama server connection and backend settings.
        </div>
       )}
    </div>
  );
};

export default Chat;