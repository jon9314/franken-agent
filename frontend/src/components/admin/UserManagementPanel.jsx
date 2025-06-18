import { useState, useEffect, useCallback } from 'react';
import apiClient from '@/api/index.js';
import { UserGroupIcon, ArrowPathIcon, InboxIcon, PlusIcon, TrashIcon } from '@heroicons/react/24/outline';
import useAuth from '@/hooks/useAuth'; // Import useAuth to get current user info

// (The Modal component code remains the same as before)
const Modal = ({ isOpen, onClose, title, children }) => {
    if (!isOpen) return null;
    return (
        <div className="relative z-50" aria-labelledby="modal-title" role="dialog" aria-modal="true">
            <div className="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity"></div>
            <div className="fixed inset-0 z-10 overflow-y-auto">
                <div className="flex min-h-full items-end justify-center p-4 text-center sm:items-center sm:p-0">
                    <div className="relative transform overflow-hidden rounded-lg bg-white text-left shadow-xl transition-all sm:my-8 sm:w-full sm:max-w-lg">
                        <div className="bg-white p-4 sm:p-6">
                            <div className="flex justify-between items-start">
                                <h3 className="text-lg font-semibold leading-6 text-gray-900" id="modal-title">{title}</h3>
                                <button onClick={onClose} className="p-1 rounded-full text-gray-400 hover:bg-gray-100">&times;</button>
                            </div>
                            <div className="mt-4">
                                {children}
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

const UserManagementPanel = () => {
    const { auth } = useAuth(); // Get the authenticated user's info
    const [users, setUsers] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState('');
    const [isModalOpen, setIsModalOpen] = useState(false);
    const [formError, setFormError] = useState('');
    const [newUser, setNewUser] = useState({
        email: '',
        password: '',
        full_name: '',
        role: 'user',
    });

    const fetchUsers = useCallback(async (showLoadingSpinner = true) => {
        if(showLoadingSpinner) setIsLoading(true);
        setError('');
        try {
            const response = await apiClient.get('/admin/users');
            setUsers(response.data);
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

    const handleInputChange = (e) => {
        const { name, value } = e.target;
        setNewUser(prev => ({ ...prev, [name]: value }));
    };

    const handleAddUser = async (e) => {
        e.preventDefault();
        setFormError('');
        if (!newUser.email || !newUser.password || !newUser.full_name) {
            setFormError("Please fill out all required fields.");
            return;
        }
        try {
            await apiClient.post('/admin/users', newUser);
            setIsModalOpen(false);
            setNewUser({ email: '', password: '', full_name: '', role: 'user' });
            await fetchUsers(false);
        } catch (err) {
            const detail = err.response?.data?.detail || "An unknown error occurred.";
            setFormError(`Failed to add user: ${detail}`);
        }
    };

    const handleDeleteUser = async (userId, userEmail) => {
        if (window.confirm(`Are you sure you want to delete the user: ${userEmail}? This action cannot be undone.`)) {
            try {
                await apiClient.delete(`/admin/users/${userId}`);
                await fetchUsers(false); // Refresh the list
            } catch (err) {
                alert(err.response?.data?.detail || 'Failed to delete user.');
            }
        }
    };

    return (
        <>
            <div className="space-y-6 h-full flex flex-col">
                 <header className="flex items-center justify-between pb-4 border-b border-gray-200">
                    <div className="flex items-center gap-3">
                        <UserGroupIcon className="h-7 w-7 text-blue-600" />
                        <h2 className="text-2xl font-semibold text-gray-800">User Management</h2>
                    </div>
                    <div className="flex items-center gap-4">
                         <button onClick={() => fetchUsers(true)} disabled={isLoading} className="p-2 rounded-md hover:bg-gray-100 text-gray-500 disabled:text-gray-300 transition-colors" title="Refresh user list">
                            <ArrowPathIcon className={`h-5 w-5 ${isLoading ? 'animate-spin' : ''}`} />
                        </button>
                        <button onClick={() => setIsModalOpen(true)} className="inline-flex items-center justify-center rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600">
                            <PlusIcon className="-ml-0.5 mr-1.5 h-5 w-5" />
                            <span>Add User</span>
                        </button>
                    </div>
                </header>

                {error && <div className="bg-red-50 border-l-4 border-red-500 text-red-700 p-4 rounded-md" role="alert"><p>{error}</p></div>}

                <div className="flex-grow overflow-x-auto shadow-md rounded-lg border border-gray-200">
                    <table className="min-w-full divide-y divide-gray-200 bg-white">
                        <thead className="bg-gray-50">
                            <tr>
                                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
                                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Full Name</th>
                                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Email</th>
                                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Role</th>
                                <th scope="col" className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {isLoading ? (
                                <tr><td colSpan="5" className="px-6 py-10 text-center text-sm text-gray-500">Loading...</td></tr>
                            ) : users.length > 0 ? users.map(user => (
                                <tr key={user.id} className="hover:bg-gray-50">
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{user.id}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">{user.full_name || <span className="italic text-gray-400">N/A</span>}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-700">{user.email}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                                        <span className={`px-2.5 py-0.5 inline-flex text-xs leading-5 font-semibold rounded-full ${user.role === 'admin' ? 'bg-green-100 text-green-800' : 'bg-blue-100 text-blue-800'}`}>
                                            {user.role.charAt(0).toUpperCase() + user.role.slice(1)}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                        {/* Prevent deleting the currently logged-in user */}
                                        {auth.user?.id !== user.id && (
                                            <button onClick={() => handleDeleteUser(user.id, user.email)} className="text-red-600 hover:text-red-900">
                                                <TrashIcon className="h-5 w-5" />
                                            </button>
                                        )}
                                    </td>
                                </tr>
                            )) : (
                                <tr>
                                    <td colSpan="5" className="px-6 py-10 text-center text-sm text-gray-500">
                                        <InboxIcon className="h-8 w-8 mx-auto text-gray-400 mb-2"/>
                                        No users found in the system.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>

            <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title="Add New User">
                <form onSubmit={handleAddUser} className="space-y-4">
                    {formError && <p className="text-sm text-red-600 bg-red-50 p-3 rounded-md">{formError}</p>}
                    <div>
                        <label className="block text-sm font-medium text-gray-700">Full Name</label>
                        <input type="text" name="full_name" value={newUser.full_name} onChange={handleInputChange} required className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"/>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700">Email</label>
                        <input type="email" name="email" value={newUser.email} onChange={handleInputChange} required className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"/>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700">Password</label>
                        <input type="password" name="password" value={newUser.password} onChange={handleInputChange} required className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm"/>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-gray-700">Role</label>
                        <select name="role" value={newUser.role} onChange={handleInputChange} className="mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-blue-500 focus:ring-blue-500 sm:text-sm">
                            <option value="user">User</option>
                            <option value="admin">Admin</option>
                        </select>
                    </div>
                    <div className="bg-gray-50 px-4 py-3 sm:flex sm:flex-row-reverse -mx-4 -mb-4 -mt-4 rounded-b-lg">
                        <button type="submit" className="inline-flex w-full justify-center rounded-md bg-blue-600 px-3 py-2 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 sm:ml-3 sm:w-auto">Create User</button>
                        <button type="button" onClick={() => setIsModalOpen(false)} className="mt-3 inline-flex w-full justify-center rounded-md bg-white px-3 py-2 text-sm font-semibold text-gray-900 shadow-sm ring-1 ring-inset ring-gray-300 hover:bg-gray-50 sm:mt-0 sm:w-auto">Cancel</button>
                    </div>
                </form>
            </Modal>
        </>
    );
};

export default UserManagementPanel;
