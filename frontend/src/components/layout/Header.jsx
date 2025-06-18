import { useState } from 'react'; // Import useState
import { Link, NavLink, useNavigate } from 'react-router-dom';
import useAuth from '@/hooks/useAuth';
import { 
    ChatBubbleLeftEllipsisIcon, 
    AcademicCapIcon, 
    Cog8ToothIcon, 
    UserCircleIcon, 
    ArrowRightOnRectangleIcon,
    UserPlusIcon,
    XMarkIcon, // Icon for closing the menu
    Bars3Icon // The "hamburger" icon
} from '@heroicons/react/24/outline';

const Header = () => {
  const { auth, logout } = useAuth();
  const navigate = useNavigate();
  const [isMenuOpen, setIsMenuOpen] = useState(false); // State to track if mobile menu is open

  const handleLogout = () => {
    setIsMenuOpen(false); // Close menu on logout
    logout();
  };

  const navLinkClasses = ({ isActive }) =>
    `px-3 py-2 rounded-md text-sm font-medium flex items-center gap-1.5 transition-colors duration-150 ease-in-out ${
      isActive 
      ? 'bg-blue-100 text-blue-700' 
      : 'text-gray-500 hover:text-gray-900 hover:bg-gray-100'
    }`;

  const mobileNavLinkClasses = ({ isActive }) =>
    `block px-3 py-2 rounded-md text-base font-medium ${
        isActive 
        ? 'bg-blue-100 text-blue-700' 
        : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
    }`;

  const buttonLinkClasses = "inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500";
  const secondaryButtonLinkClasses = "text-gray-500 hover:text-gray-900 px-3 py-2 rounded-md text-sm font-medium";

  const MobileNavLinks = () => (
    <>
        <NavLink to="/chat" className={mobileNavLinkClasses} onClick={() => setIsMenuOpen(false)}>Chat</NavLink>
        <NavLink to="/genealogy" className={mobileNavLinkClasses} onClick={() => setIsMenuOpen(false)}>Genealogy</NavLink>
        {auth.user?.role === 'admin' && (
          <NavLink to="/admin" className={mobileNavLinkClasses} onClick={() => setIsMenuOpen(false)}>Admin Panel</NavLink>
        )}
    </>
  );

  return (
    <header className="bg-white shadow-sm sticky top-0 z-50 border-b border-gray-200">
      <nav className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo / App Name */}
          <div className="flex items-center">
            <Link to="/" className="text-2xl font-bold text-blue-600 hover:text-blue-700 transition-colors" onClick={() => setIsMenuOpen(false)}>
              Frankie
            </Link>
          </div>

          {/* Desktop Navigation Links */}
          <div className="hidden md:flex items-center space-x-1">
            {auth?.token && auth?.user && <MobileNavLinks />}
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
                <NavLink to="/login" className={secondaryButtonLinkClasses}>Login</NavLink>
                <NavLink to="/register" className={buttonLinkClasses + " flex items-center gap-1.5"}>
                   <UserPlusIcon className="h-5 w-5" /> Register
                </NavLink>
              </>
            )}
          </div>

          {/* Mobile Menu Button */}
          <div className="md:hidden flex items-center">
            <button 
                onClick={() => setIsMenuOpen(!isMenuOpen)} 
                type="button" 
                className="text-gray-500 hover:text-gray-700 focus:outline-none focus:ring-2 focus:ring-inset focus:ring-blue-500"
                aria-controls="mobile-menu"
                aria-expanded={isMenuOpen}
            >
              <span className="sr-only">Open main menu</span>
              {isMenuOpen ? <XMarkIcon className="h-6 w-6" /> : <Bars3Icon className="h-6 w-6" />}
            </button>
          </div>
        </div>
      </nav>

      {/* Mobile Menu Panel */}
      {isMenuOpen && (
        <div className="md:hidden" id="mobile-menu">
            <div className="px-2 pt-2 pb-3 space-y-1 sm:px-3">
                {auth?.token && auth?.user ? (
                    <>
                        <MobileNavLinks />
                        <div className="pt-4 mt-4 border-t border-gray-200">
                            <div className="flex items-center px-3">
                                <UserCircleIcon className="h-8 w-8 text-gray-400" />
                                <div className="ml-3">
                                    <div className="text-base font-medium text-gray-800">{auth.user.full_name || auth.user.email}</div>
                                    <div className="text-sm font-medium text-gray-500">{auth.user.email}</div>
                                </div>
                            </div>
                            <div className="mt-3 space-y-1">
                                <button onClick={handleLogout} className="w-full text-left block px-3 py-2 rounded-md text-base font-medium text-gray-600 hover:bg-gray-100 hover:text-gray-900">
                                    Logout
                                </button>
                            </div>
                        </div>
                    </>
                ) : (
                    <>
                       <NavLink to="/login" className={mobileNavLinkClasses} onClick={() => setIsMenuOpen(false)}>Login</NavLink>
                       <NavLink to="/register" className={mobileNavLinkClasses} onClick={() => setIsMenuOpen(false)}>Register</NavLink>
                    </>
                )}
            </div>
        </div>
      )}
    </header>
  );
};

export default Header;
