import { Link, useNavigate } from 'react-router-dom';
import RegisterForm from '@/components/auth/RegisterForm'; // Ensure path is correct
import useAuth from '@/hooks/useAuth';
import { useEffect } from 'react';

const Register = () => {
  const navigate = useNavigate();
  const { auth } = useAuth();

  useEffect(() => {
    // If user is already logged in, redirect them from the register page
    if (auth.token && auth.user) {
      navigate('/', { replace: true });
    }
  }, [auth, navigate]);

  return (
    <div className="min-h-[calc(100vh-10rem)] flex flex-col items-center justify-center py-8 px-4 sm:px-6 lg:px-8">
      <div className="w-full max-w-md space-y-8 p-8 sm:p-10 bg-white shadow-2xl rounded-xl border border-gray-200">
        <div>
          <h2 className="mt-6 text-center text-3xl font-bold tracking-tight text-gray-900">
            Create your Frankie account
          </h2>
          <p className="mt-2 text-center text-sm text-gray-600">
            Already have an account?{' '}
            <Link to="/login" className="font-medium text-blue-600 hover:text-blue-500">
              Sign in instead
            </Link>
          </p>
        </div>
        <RegisterForm />
      </div>
    </div>
  );
};

export default Register;