import { NavLink, Outlet, useLocation, Navigate } from 'react-router-dom';
import { 
    UsersIcon, 
    CpuChipIcon, 
    ShieldCheckIcon, 
    Cog6ToothIcon, 
    DocumentMagnifyingGlassIcon,
    HomeIcon
} from '@heroicons/react/24/outline';
import useAuth from '@/hooks/useAuth';

const Admin = () => {
    const location = useLocation();
    const { auth } = useAuth();

    // This is a secondary check; RequireAuth should handle this primarily.
    if (!auth.isLoading && auth.user?.role !== 'admin') {
        return <Navigate to="/" replace />;
    }

    const navLinkClasses = (path) => {
        // For nested routes, ensure the base path also highlights.
        // e.g., viewing /admin/agent/task/1 should keep /admin/agent highlighted.
        const isActive = location.pathname === path || 
                         (path !== "/admin" && location.pathname.startsWith(path) && path.split('/').length <= location.pathname.split('/').length);
        
        return `group flex items-center px-3 py-2.5 text-sm font-medium rounded-md transition-colors duration-150 ease-in-out focus:outline-none focus:ring-2 focus:ring-blue-500 ${
            isActive 
            ? 'bg-blue-100 text-blue-700' 
            : 'text-gray-600 hover:bg-gray-100 hover:text-gray-900'
        }`;
    };
    
    const adminNavLinks = [
        { path: "/admin/users", name: "User Management", icon: UsersIcon },
        { path: "/admin/agent", name: "Agent Tasks", icon: CpuChipIcon },
        { path: "/admin/permissions", name: "Agent Permissions", icon: ShieldCheckIcon },
        { path: "/admin/genealogy-review", name: "Genealogy Review", icon: DocumentMagnifyingGlassIcon },
        { path: "/admin/settings", name: "Settings", icon: Cog6ToothIcon },
    ];

    return (
        <div className="flex flex-col md:flex-row gap-6 md:gap-8 min-h-[calc(100vh-8rem)]">
            {/* Sidebar Navigation */}
            <aside className="md:w-64 lg:w-72 flex-shrink-0 bg-white p-4 md:p-5 shadow-lg rounded-lg border border-gray-200">
                <h1 className="text-xl md:text-2xl font-bold text-gray-800 mb-6 px-1">Admin Dashboard</h1>
                <nav className="space-y-1.5">
                    {adminNavLinks.map(link => (
                         <NavLink 
                            key={link.name} 
                            to={link.path} 
                            className={() => navLinkClasses(link.path)}
                        >
                            <link.icon className="h-5 w-5 mr-3 flex-shrink-0" aria-hidden="true" />
                            <span className="truncate">{link.name}</span>
                        </NavLink>
                    ))}
                </nav>
            </aside>

            {/* Main Content Area for Admin Sections */}
            <main className="flex-1 bg-white p-4 md:p-6 shadow-lg rounded-lg border border-gray-200 overflow-y-auto">
                <Outlet /> {/* This is where the content of /admin/users, /admin/agent, etc. will be rendered */}
            </main>
        </div>
    );
};

export default Admin;