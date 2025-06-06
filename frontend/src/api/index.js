import axios from 'axios';

// Determine the API base URL.
// For development, Vite's proxy in `vite.config.js` handles '/api' and routes it to the backend.
// For production builds, it assumes the API is served under the same domain at '/api/v1'.
// If `VITE_API_BASE_URL` is set in the .env file, it will be used directly.
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000, // Set a reasonable timeout (e.g., 30 seconds)
});

// --- Request Interceptor ---
// This interceptor runs before each request is sent.
// It retrieves the JWT token from localStorage and adds it to the Authorization header.
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('frankie_token'); // Use a consistent key for the token
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    // Handle request errors (e.g., network issues before request is sent)
    return Promise.reject(error);
  }
);

// --- Response Interceptor (Optional but Recommended) ---
// This interceptor runs after a response is received.
// It can be used to handle global API errors, like 401 Unauthorized.
apiClient.interceptors.response.use(
  (response) => {
    // Any status code that lie within the range of 2xx cause this function to trigger
    return response;
  },
  (error) => {
    // Any status codes that falls outside the range of 2xx cause this function to trigger
    if (error.response) {
      // The request was made and the server responded with a status code
      // that falls out of the range of 2xx
      if (error.response.status === 401) {
        // Handle 401 Unauthorized globally
        // This could be due to an expired token or invalid token.
        // It's often a good idea to clear the token and redirect to login.
        // However, direct navigation from here can be problematic.
        // It's better to let the AuthProvider handle the logout state change.
        // For now, we can log it and potentially trigger an event or rely on AuthProvider's check.
        console.error("API Error: 401 Unauthorized. Token might be invalid or expired.");
        // Consider removing the token if the server explicitly says it's invalid.
        // localStorage.removeItem('frankie_token');
        // window.dispatchEvent(new Event('auth-error-401')); // Custom event for AuthProvider
      } else if (error.response.status === 403) {
        console.error("API Error: 403 Forbidden. User does not have permission.");
      } else if (error.response.status >= 500) {
        console.error("API Error: Server error.", error.response.data);
      }
    } else if (error.request) {
      // The request was made but no response was received
      console.error("API Error: No response received from server.", error.request);
    } else {
      // Something happened in setting up the request that triggered an Error
      console.error('API Error: Error setting up request.', error.message);
    }
    return Promise.reject(error);
  }
);

export default apiClient;