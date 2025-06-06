import { Link, useLocation, useNavigate } from 'react-router-dom';
import LoginForm from '@/components/auth/LoginForm'; // Ensure path is correct
import useAuth from '@/hooks/useAuth'; // To check if user is already logged in
import { useEffect } from 'react';

const Login = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const { auth } = useAuth();
  const message = location.state?.message; // For messages like "Registration successful!"

  useEffect(() => {
    // If user is already logged in, redirect them from the login page
    if (auth.token && auth.user) {
      navigate(location.state?.from?.pathname || '/', { replace: true });
    }
  }, [auth, navigate, location.state]);


  return (
    <div className="min-h-[calc(100vh-10rem)] flex flex-col items-center justify-center py-8 px-4 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-8 p-8 sm:p-10 bg-white shadow-2xl rounded-xl border border-gray-200">
        <div>
          <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
            Sign in to Frankie
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Or if you don't have an account,{' '}
            <Link to="/register" className="font-medium text-blue-600 hover:text-blue-500">
              create a new one
            </Link>
          </p>
        </div>
        {message && (
          <div className="bg-green-50 border-l-4 border-green-400 p-4 rounded-md my-4">
            <div className="flex">
              <div className="flex-shrink-0">
                {/* Heroicon name: check-circle */}
                <svg className="h-5 w-5 text-green-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true">
                  <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm font-medium text-green-700">{message}</p>
              </div>
            </div>
          </div>
        )}
        <LoginForm />
      </div>
    </div>
  );
};

export default Login;