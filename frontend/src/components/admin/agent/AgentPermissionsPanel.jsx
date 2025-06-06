import { useState, useEffect, useCallback } from 'react';
import apiClient from '@/api/index.js';
import { TrashIcon, PlusCircleIcon, ShieldExclamationIcon, ArrowPathIcon, InboxIcon } from '@heroicons/react/24/outline';
import { format } from 'date-fns';

const AgentPermissionsPanel = () => {
    const [permissions, setPermissions] = useState([]);
    const [newPath, setNewPath] = useState('');
    const [newComment, setNewComment] = useState('');
    const [isLoading, setIsLoading] = useState(true);
    const [error, setError] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);

    const fetchPermissions = useCallback(async (showLoadingSpinner = true) => {
        if(showLoadingSpinner) setIsLoading(true);
        setError('');
        try {
            const response = await apiClient.get('/admin/agent/permissions');
            setPermissions(response.data);
        } catch (err) {
            setError('Failed to fetch permissions. Ensure the backend is running and you have admin rights.');
            console.error("Fetch permissions error:", err);
        } finally {
            if(showLoadingSpinner) setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchPermissions();
    }, [fetchPermissions]);

    const handleAddPermission = async (e) => {
        e.preventDefault();
        if (!newPath.trim()) {
            setError("Path cannot be empty.");
            return;
        }
        setIsSubmitting(true);
        setError('');
        try {
            await apiClient.post('/admin/agent/permissions', { path: newPath.trim(), comment: newComment.trim() });
            setNewPath('');
            setNewComment('');
            await fetchPermissions(false); // Refresh list without global loading indicator
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to add permission. Path might already exist or be invalid.');
        } finally {
            setIsSubmitting(false);
        }
    };

    const handleDeletePermission = async (permissionId) => {
        if (!window.confirm("Are you sure you want to delete this permission? The Code Modifier agent will no longer be able to access this path.")) return;
        
        try {
            await apiClient.delete(`/admin/agent/permissions/${permissionId}`);
            await fetchPermissions(false); // Refresh list
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to delete permission.');
        }
    };

    return (
        <div className="space-y-8 h-full flex flex-col">
            <header className="flex items-center justify-between pb-4 border-b border-gray-200">
                <div className="flex items-center gap-3">
                    <ShieldExclamationIcon className="h-7 w-7 text-blue-600" />
                    <h2 className="text-2xl font-semibold text-gray-800">Code Agent Permissions</h2>
                </div>
                 <button onClick={() => fetchPermissions(true)} disabled={isLoading} className="p-2 rounded-md hover:bg-gray-100 text-gray-500 disabled:text-gray-300 transition-colors" title="Refresh permissions list">
                    <ArrowPathIcon className={`h-5 w-5 ${isLoading ? 'animate-spin' : ''}`} />
                </button>
            </header>
             
            {error && <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 rounded-md" role="alert"><p>{error}</p></div>}

            <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200">
                <p className="text-sm text-gray-600 mb-4">
                    Define the exact files or directories the Code Modifier plugin is allowed to access. Add a trailing slash (e.g., <code className="bg-gray-200 px-1 rounded text-xs">backend/app/services/</code>) to allow access to an entire directory. If this list is empty, the agent cannot access any files.
                </p>
                
                <form onSubmit={handleAddPermission} className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6 pb-6 items-end border-b border-gray-200">
                    <div className="md:col-span-1">
                        <label htmlFor="path-permission" className="block text-sm font-medium text-gray-700 mb-1">Allowed Path</label>
                        <input type="text" id="path-permission" value={newPath} onChange={(e) => setNewPath(e.target.value)}
                            className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                            placeholder="e.g., backend/app/services/"
                        />
                    </div>
                     <div className="md:col-span-1">
                        <label htmlFor="comment-permission" className="block text-sm font-medium text-gray-700 mb-1">Comment (Optional)</label>
                         <input type="text" id="comment-permission" value={newComment} onChange={(e) => setNewComment(e.target.value)}
                            className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                            placeholder="Reason for this permission"
                        />
                    </div>
                    <div className="md:col-span-1">
                        <button type="submit" disabled={isSubmitting} className="w-full inline-flex items-center justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:bg-gray-400">
                            <PlusCircleIcon className="h-5 w-5 mr-2" />
                            {isSubmitting ? 'Adding...' : 'Add Allowed Path'}
                        </button>
                    </div>
                </form>

                <h3 className="text-lg font-semibold text-gray-700 mb-3">Current Allowed Paths</h3>
                <div className="flex-grow overflow-x-auto shadow-md rounded-lg border border-gray-200">
                    <table className="min-w-full divide-y divide-gray-200 bg-white">
                        <thead className="bg-gray-50 sticky top-0">
                            <tr>
                                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Path</th>
                                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Comment</th>
                                <th scope="col" className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Added On</th>
                                <th scope="col" className="px-6 py-3 text-center text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                             {isLoading && !permissions.length ? (
                                <tr><td colSpan="4" className="px-6 py-10 text-center text-sm text-gray-500">Loading...</td></tr>
                            ) : permissions.length > 0 ? permissions.map((perm) => (
                                <tr key={perm.id} className="hover:bg-slate-50">
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-800 font-mono">{perm.path}</td>
                                    <td className="px-6 py-4 text-sm text-gray-600 max-w-xs truncate hover:whitespace-normal" title={perm.comment}>{perm.comment || <span className="italic text-gray-400">N/A</span>}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{format(new Date(perm.created_at), 'PP')}</td>
                                    <td className="px-6 py-4 whitespace-nowrap text-center text-sm font-medium">
                                        <button onClick={() => handleDeletePermission(perm.id)} className="text-red-500 hover:text-red-700 p-1.5 rounded-full hover:bg-red-100 transition-colors" title="Delete Permission">
                                            <TrashIcon className="h-4 w-4" />
                                        </button>
                                    </td>
                                </tr>
                            )) : (
                                <tr>
                                    <td colSpan="4" className="px-6 py-10 text-center text-sm text-gray-500">
                                        <InboxIcon className="h-8 w-8 mx-auto text-gray-400 mb-2"/>
                                        No permissions defined. The Code Agent plugin cannot modify any files.
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default AgentPermissionsPanel;