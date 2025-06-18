import { createContext, useState, useEffect, useCallback } from 'react';
import { jwtDecode } from 'jwt-decode'; // For decoding JWT tokens
import apiClient from '@/api/index.js'; // Ensure path is correct for your API client
import { useNavigate, useLocation } from 'react-router-dom';

const AuthContext = createContext({}); // Initialize with an empty object

export const AuthProvider = ({ children }) => {
  // Initialize auth state: token, user profile, and loading status
  const [auth, setAuth] = useState({
    token: localStorage.getItem('frankie_token') || null, // Persist token from localStorage
    user: null,
    isLoading: true, // Start in loading state until token/user is verified
  });

  const navigate = useNavigate();
  const location = useLocation(); // To redirect user back after login

  // Function to fetch user details using a valid token
  const fetchUserDetails = useCallback(async (currentToken) => {
    if (!currentToken) {
      setAuth({ token: null, user: null, isLoading: false });
      return;
    }
    try {
      // apiClient's request interceptor should add the token, but good practice to be explicit here if needed
      const response = await apiClient.get('/auth/me'); // Endpoint to get current user info
      setAuth({ token: currentToken, user: response.data, isLoading: false });
    } catch (error) {
      console.error("AuthProvider: Failed to fetch user details with token.", error);
      localStorage.removeItem('frankie_token'); // Token is invalid, remove it
      setAuth({ token: null, user: null, isLoading: false });
    }
  }, []); // Removed navigate from dependencies as it might cause loops if not careful

  // Effect to initialize auth state on component mount or when token changes externally
  useEffect(() => {
    const initialToken = localStorage.getItem('frankie_token');
    if (initialToken) {
      try {
        const decodedToken = jwtDecode(initialToken);
        const currentTime = Date.now() / 1000; // Convert to seconds
        if (decodedToken.exp < currentTime) {
          // Token is expired
          console.log("AuthProvider: Token expired on initial load.");
          localStorage.removeItem('frankie_token');
          setAuth({ token: null, user: null, isLoading: false });
        } else {
          // Token is valid and not expired, fetch user details
          fetchUserDetails(initialToken);
        }
      } catch (error) {
        // Token is invalid (e.g., malformed)
        console.error("AuthProvider: Invalid token on initial load.", error);
        localStorage.removeItem('frankie_token');
        setAuth({ token: null, user: null, isLoading: false });
      }
    } else {
      // No token found in localStorage
      setAuth({ token: null, user: null, isLoading: false });
    }
  }, [fetchUserDetails]); // Run only when fetchUserDetails changes (which is stable)

  const login = async (email, password) => {
    const formData = new URLSearchParams();
    formData.append('username', email); // Backend OAuth2 form expects 'username' for email
    formData.append('password', password);

    try {
      const response = await apiClient.post('/auth/token', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      });
      
      const newAccessToken = response.data.access_token;
      localStorage.setItem('frankie_token', newAccessToken);
      
      // After setting the token, fetch user details to update the auth context fully
      await fetchUserDetails(newAccessToken); 
      
      // Redirect to the page the user was trying to access, or to home
      const fromPath = location.state?.from?.pathname || '/';
      navigate(fromPath, { replace: true });
    } catch (error) {
      // Re-throw the error so the login form can catch it and display a message
      console.error("AuthProvider: Login failed", error.response?.data?.detail || error.message);
      throw error; 
    }
  };

  const register = async (email, password, fullName) => {
    // Role is typically assigned by the backend on registration (e.g., default 'user')
    // Client-side should not dictate role for security reasons.
    try {
      await apiClient.post('/auth/register', { email, password, full_name: fullName, role: "user" });
      // After successful registration, guide the user to the login page
      navigate('/login', { state: { message: 'Registration successful! Please log in.' } });
    } catch (error) {
      console.error("AuthProvider: Registration failed", error.response?.data?.detail || error.message);
      throw error;
    }
  };
  
  const logout = useCallback(() => {
    console.log("AuthProvider: Logging out user.");
    setAuth({ token: null, user: null, isLoading: false });
    localStorage.removeItem('frankie_token');
    // Optionally clear other user-related data from storage
    navigate('/login'); // Redirect to login page after logout
  }, [navigate]);

  return (
    <AuthContext.Provider value={{ auth, setAuth, login, logout, register }}>
      {/* Avoid rendering children until loading state is false to prevent flicker or auth issues */}
      {!auth.isLoading ? children : <div className="flex items-center justify-center min-h-screen"><div>Loading Application...</div></div>}
    </AuthContext.Provider>
  );
};

export default AuthContext;
