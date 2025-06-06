import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx' // The root component of the application
import './index.css'      // Import global styles and Tailwind CSS
import { BrowserRouter } from 'react-router-dom' // For client-side routing
import { AuthProvider } from './context/AuthProvider.jsx' // Global authentication context

// Get the root DOM element
const rootElement = document.getElementById('root');

if (rootElement) {
  ReactDOM.createRoot(rootElement).render(
    <React.StrictMode>
      <BrowserRouter>
        <AuthProvider>
          <App />
        </AuthProvider>
      </BrowserRouter>
    </React.StrictMode>,
  );
} else {
  console.error("Failed to find the root element. Ensure your HTML has an element with id='root'.");
}