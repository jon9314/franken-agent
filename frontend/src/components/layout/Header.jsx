import { Link, NavLink, useNavigate } from 'react-router-dom';
import useAuth from '@/hooks/useAuth'; // Ensure path is correct
import { 
    ChatBubbleLeftEllipsisIcon, 
    AcademicCapIcon, 
    Cog8ToothIcon, 
    UserCircleIcon, 
    ArrowRightOnRectangleIcon,
    UserPlusIcon
} from '@heroicons/react/24/outline'; // Using outline icons for a consistent look

const Header = () => {
  const { auth, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout(); // This will navigate to /login via AuthProvider
  };

  const navLinkClasses = ({ isActive }) =>
    `px-3 py-2 rounded-md text-sm font-medium flex items-center gap-1.5 transition-colors duration-150 ease-in-out ${
      isActive 
      ? 'bg-blue-100 text-blue-700' 
      : 'text-gray-500 hover:text-gray-900 hover:bg-gray-100'
    }`;
  
  const buttonLinkClasses = "inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500";
  const secondaryButtonLinkClasses = "text-gray-500 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium";


  return (
    <header className="bg-white shadow-sm sticky top-0 z-50 border-b border-gray-200">
      <nav className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo / App Name */}
          <div className="flex items-center">
            <Link to="/" className="text-2xl font-bold text-blue-600 hover:text-blue-700 transition-colors">
              Frankie
            </Link>
          </div>

          {/* Desktop Navigation Links */}
          <div className="hidden md:flex items-center space-x-1">
            {auth?.token && auth?.user ? (
              <>
                <NavLink to="/chat" className={navLinkClasses}>
                  <ChatBubbleLeftEllipsisIcon className="h-5 w-5" /> Chat
                </NavLink>
                <NavLink to="/genealogy" className={navLinkClasses}>
                  <AcademicCapIcon className="h-5 w-5" /> Genealogy
                </NavLink>
                {auth.user?.role === 'admin' && (
                  <NavLink to="/admin" className={navLinkClasses}>
                    <Cog8ToothIcon className="h-5 w-5" /> Admin Panel
                  </NavLink>
                )}
              </>
            ) : null}
          </div>
          
          {/* Auth Links / User Info */}
          <div className="hidden md:flex items-center space-x-4">
            {auth?.token && auth?.user ? (
              <>
                <div className="flex items-center text-sm text-gray-700">
                  <UserCircleIcon className="h-5 w-5 mr-1.5 text-gray-400" />
                  {auth.user.full_name || auth.user.email}
                </div>
                <button 
                  onClick={handleLogout} 
                  className="text-gray-500 hover:text-gray-900 hover:bg-gray-100 px-3 py-2 rounded-md text-sm font-medium flex items-center gap-1.5 transition-colors" 
                  title="Logout"
                >
                  <ArrowRightOnRectangleIcon className="h-5 w-5" />
                  Logout
                </button>
              </>
            ) : (
              <>
                <NavLink to="/login" className={secondaryButtonLinkClasses}>
                  Login
                </NavLink>
                <NavLink to="/register" className={buttonLinkClasses + " flex items-center gap-1.5"}>
                   <UserPlusIcon className="h-5 w-5" /> Register
                </NavLink>
              </>
            )}
          </div>
          
          {/* Mobile Menu Button (Placeholder - functionality to be added if needed) */}
          <div className="md:hidden flex items-center">
            <button type="button" className="text-gray-500 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500">
              <span className="sr-only">Open main menu</span>
              {/* Heroicon name: menu (outline) */}
              <svg className="h-6 w-6" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden="true">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          </div>
        </div>
      </nav>
      {/* Mobile Menu Panel (Placeholder - functionality to be added if needed) */}
    </header>
  );
};

export default Header;