import axios from 'axios';

// Determine the API base URL.
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
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    // Handle request errors (e.g., network issues before request is sent)
    return Promise.reject(error);
  }
);

// --- Response Interceptor (Optional but Recommended) ---
// This can be used to handle global API errors, like 401 Unauthorized,
// which could trigger an automatic logout.
apiClient.interceptors.response.use(
  (response) => {
    // Any status code that lie within the range of 2xx cause this function to trigger
    return response;
  },
  (error) => {
    // Any status codes that falls outside the range of 2xx cause this function to trigger
    if (error.response && error.response.status === 401) {
      // Handle 401 Unauthorized globally
      console.error("API Error: 401 Unauthorized. Token might be invalid or expired.");
      // Optionally, you could trigger a logout here:
      // localStorage.removeItem('frankie_token');
      // window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default apiClient;
