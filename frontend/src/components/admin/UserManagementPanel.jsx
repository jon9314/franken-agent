import { useState, useEffect, useCallback } from 'react';
import apiClient from '@/api/index.js';
import { UserGroupIcon, ArrowPathIcon, InboxIcon } from '@heroicons/react/24/outline';

const UserManagementPanel = () => {
    const [users, setUsers] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState('');

    const fetchUsers = useCallback(async (showLoadingSpinner = true) => {
        if(showLoadingSpinner) setIsLoading(true);
        try {
            const response = await apiClient.get('/admin/users');
            setUsers(response.data);
            setError('');
        } catch (err) {
            setError('Failed to fetch user data. You might not have the correct permissions or the server might be down.');
            console.error("Fetch users error:", err);
        } finally {
            if(showLoadingSpinner) setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchUsers();
    }, [fetchUsers]);

    return (
        <div className="space-y-6 h-full flex flex-col">
            <header className="flex items-center justify-between pb-4 border-b border-gray-200">
                <div className="flex items-center gap-3">
                    <UserGroupIcon className="h-7 w-7 text-blue-600" />
                    <h2 className="text-2xl font-semibold text-gray-800">User Management</h2>
                </div>
                <button
                    onClick={() => fetchUsers(true)}
                    disabled={isLoading}
                    className="p-2 rounded-md hover:bg-gray-100 text-gray-500 disabled:text-gray-300 transition-colors"
                    title="Refresh user list"
                >
                    <ArrowPathIcon className={`h-5 w-5 ${isLoading ? 'animate-spin' : ''}`} />
                </button>
            </header>

            {error && <div className="bg-red-50 border-l-4 border-red-500 text-red-700 p-4 rounded-md" role="alert"><p>{error}</p></div>}
            
            <div className="flex-grow overflow-x-auto shadow-md rounded-lg border border-gray-200">
                <table className="min-w-full divide-y divide-gray-200 bg-white">
                    <thead className="bg-gray-50 sticky top-0">
                        <tr>
                            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
                            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Full Name</th>
                            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Email</th>
                            <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Role</th>
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-200">
                        {isLoading ? (
                             <tr>
                                <td colSpan="4" className="px-6 py-10 text-center text-sm text-gray-500">Loading users...</td>
                            </tr>
                        ) : users.length > 0 ? users.map(user => (
                            <tr key={user.id} className="hover:bg-gray-50">
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{user.id}</td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{user.full_name || <span className="italic text-gray-400">N/A</span>}</td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{user.email}</td>
                                <td className="px-6 py-4 whitespace-nowrap text-sm">
                                    <span className={`px-2.5 py-0.5 inline-flex text-xs leading-5 font-semibold rounded-full ${
                                        user.role === 'admin' 
                                        ? 'bg-green-100 text-green-800' 
                                        : 'bg-blue-100 text-blue-800'
                                    }`}>
                                        {user.role.charAt(0).toUpperCase() + user.role.slice(1)}
                                    </span>
                                </td>
                            </tr>
                        )) : (
                            <tr>
                                <td colSpan="4" className="px-6 py-10 text-center text-sm text-gray-500">
                                     <InboxIcon className="h-8 w-8 mx-auto text-gray-400 mb-2"/>
                                    No users found in the system.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default UserManagementPanel;