import { useState, useEffect, useCallback } from 'react';
import apiClient from '@/api/index.js';
import { Link } from 'react-router-dom';
import { 
    CpuChipIcon, LightBulbIcon, DocumentTextIcon, ClockIcon, EyeIcon, 
    CodeBracketIcon, ArrowPathIcon, InboxIcon, BeakerIcon 
} from '@heroicons/react/24/outline';
import { format } from 'date-fns';

const getStatusPillClasses = (status) => {
    const base = "px-2.5 py-1 text-xs font-semibold rounded-full inline-block leading-tight";
    switch (status) {
        case 'PENDING': return `${base} bg-slate-200 text-slate-800`;
        case 'PLANNING': return `${base} bg-purple-200 text-purple-800 animate-pulse`;
        case 'ANALYZING': return `${base} bg-yellow-200 text-yellow-800 animate-pulse`;
        case 'TESTING': return `${base} bg-orange-200 text-orange-800 animate-pulse`;
        case 'AWAITING_REVIEW': return `${base} bg-blue-200 text-blue-800`;
        case 'EXECUTING_MILESTONE': return `${base} bg-teal-200 text-teal-800 animate-pulse`;
        case 'APPLIED': return `${base} bg-green-200 text-green-800`;
        case 'REJECTED': return `${base} bg-pink-200 text-pink-800`;
        case 'ERROR': return `${base} bg-red-200 text-red-800`;
        default: return `${base} bg-gray-200 text-gray-800`;
    }
};

const AgentDashboard = () => {
    const [prompt, setPrompt] = useState('');
    const [targetFiles, setTargetFiles] = useState(''); // For code_modifier
    const [targetPersonId, setTargetPersonId] = useState(''); // For genealogy_researcher
    const [tasks, setTasks] = useState([]);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [formError, setFormError] = useState('');
    const [listError, setListError] = useState('');
    const [plugins, setPlugins] = useState([]);
    const [selectedPlugin, setSelectedPlugin] = useState('');
    const [gitStatus, setGitStatus] = useState(null);
    const [isLoadingTasks, setIsLoadingTasks] = useState(true);

    const fetchTasks = useCallback(async () => {
        try {
            const response = await apiClient.get('/admin/agent/tasks');
            setTasks(response.data);
            setListError('');
        } catch (err) {
            console.error('Failed to fetch tasks:', err);
            setListError('Failed to load task history.');
        } finally {
            setIsLoadingTasks(false);
        }
    }, []);

    const fetchPlugins = useCallback(async () => {
        try {
            const response = await apiClient.get('/admin/agent/plugins');
            setPlugins(response.data);
            if (response.data.length > 0 && !selectedPlugin) {
                const codeModifierPlugin = response.data.find(p => p.id === 'code_modifier');
                setSelectedPlugin(codeModifierPlugin ? codeModifierPlugin.id : response.data[0].id);
            }
        } catch (err) {
            console.error("Failed to fetch plugins:", err);
            setFormError((prev) => prev ? `${prev} | Failed to load plugins.` : "Failed to load plugins.");
        }
    }, [selectedPlugin]);
    
    const fetchGitStatus = useCallback(async (showLoading = false) => {
        if(showLoading) setGitStatus(prev => ({...prev, isLoading: true}));
        try {
            const response = await apiClient.get('/admin/agent/git/status');
            setGitStatus({...response.data, isLoading: false, error: null});
        } catch (err) {
            console.error("Failed to fetch git status:", err);
            setGitStatus({ error: "Could not fetch Git status from backend.", isLoading: false});
        }
    }, []);


    useEffect(() => {
        fetchPlugins();
        fetchTasks();
        fetchGitStatus(true);
        const interval = setInterval(() => { fetchTasks(); fetchGitStatus(); }, 15000);
        return () => clearInterval(interval);
    }, [fetchTasks, fetchPlugins, fetchGitStatus]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        setIsSubmitting(true);
        setFormError('');
        if (!selectedPlugin) {
            setFormError("Please select a plugin.");
            setIsSubmitting(false);
            return;
        }
        
        const taskData = { prompt: prompt.trim(), plugin_id: selectedPlugin };

        if (selectedPlugin === 'code_modifier') {
            if (!targetFiles.trim()) {
                setFormError("Target files are required for the Code Modifier plugin.");
                setIsSubmitting(false);
                return;
            }
            taskData.target_files = targetFiles.trim();
        } else if (selectedPlugin === 'genealogy_researcher') {
            if (!targetPersonId.trim() || !/^\d+$/.test(targetPersonId.trim())) {
                setFormError("A valid numeric Target Person ID is required for the Genealogy Researcher plugin.");
                setIsSubmitting(false);
                return;
            }
            taskData.target_person_id = parseInt(targetPersonId.trim(), 10);
        } else if (selectedPlugin === 'odyssey_agent') {
            if (!prompt.trim()) {
                setFormError("A detailed prompt outlining the goal is required for the Odyssey Agent.");
                setIsSubmitting(false);
                return;
            }
        }

        try {
            await apiClient.post('/admin/agent/tasks', taskData);
            setPrompt('');
            setTargetFiles('');
            setTargetPersonId('');
            await fetchTasks();
        } catch (err) {
            setFormError(err.response?.data?.detail || 'Failed to create task. Please check your input and permissions.');
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="space-y-8">
            <header className="flex items-center justify-between pb-4 border-b border-gray-200">
                <div className="flex items-center gap-3">
                    <CpuChipIcon className="h-8 w-8 text-blue-600" />
                    <h2 className="text-2xl font-semibold text-gray-800">Agent Control Center</h2>
                </div>
                 <button onClick={() => fetchGitStatus(true)} disabled={gitStatus?.isLoading} className="p-1.5 rounded-md hover:bg-gray-100 text-gray-400 hover:text-gray-600 disabled:text-gray-300" title="Refresh Git status">
                    <ArrowPathIcon className={`h-5 w-5 ${gitStatus?.isLoading ? 'animate-spin' : ''}`} />
                </button>
            </header>

            {gitStatus && (
                <div className={`p-3 rounded-md text-sm shadow-sm border ${gitStatus.error ? 'bg-red-50 text-red-700 border-red-300' : 'bg-slate-50 text-slate-700 border-slate-300'}`}>
                    {gitStatus.isLoading ? <span className="italic">Loading Git status...</span> : 
                     gitStatus.error ? gitStatus.error : 
                    <span className="flex items-center gap-2 flex-wrap">
                        <CodeBracketIcon className="h-5 w-5 flex-shrink-0"/>
                        <span className="font-medium">Git Status:</span> 
                        <span>Branch <code className="font-mono bg-slate-200 px-1.5 py-0.5 rounded text-xs">{gitStatus.active_branch}</code></span> | 
                        <span>Last Commit: <code className="font-mono bg-slate-200 px-1.5 py-0.5 rounded text-xs">{gitStatus.latest_commit}</code></span> | 
                        <span>Uncommitted: <span className={`font-semibold ${gitStatus.uncommitted_changes ? 'text-yellow-600' : 'text-green-600'}`}>{gitStatus.uncommitted_changes ? 'Yes' : 'No'}</span></span>
                    </span>
                    }
                </div>
            )}

            <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200">
                <h3 className="text-lg font-semibold text-gray-700 mb-4 border-b pb-3">Create New Agent Task</h3>
                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label htmlFor="plugin" className="block text-sm font-medium text-gray-700 mb-1">Select Plugin</label>
                        <select
                            id="plugin"
                            value={selectedPlugin}
                            onChange={(e) => { setSelectedPlugin(e.target.value); setFormError(''); }}
                            className="mt-1 block w-full pl-3 pr-10 py-2 text-base border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md shadow-sm"
                        >
                            <option value="" disabled>-- Select a Plugin --</option>
                            {plugins.map(plugin => (
                                <option key={plugin.id} value={plugin.id}>
                                    {plugin.name}
                                </option>
                            ))}
                        </select>
                         {selectedPlugin && <p className="mt-1 text-xs text-gray-500 italic">{plugins.find(p=>p.id === selectedPlugin)?.description}</p>}
                    </div>
                    <div>
                        <label htmlFor="prompt" className="block text-sm font-medium text-gray-700 mb-1">
                            <LightBulbIcon className="h-5 w-5 inline mr-1.5 text-yellow-500" />
                            Task Instruction / High-Level Goal
                        </label>
                        <textarea id="prompt" rows="4" value={prompt} onChange={(e) => setPrompt(e.target.value)} required
                            className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                            placeholder={
                                selectedPlugin === 'code_modifier' ? "e.g., 'Refactor the user authentication logic in auth.py...'" :
                                selectedPlugin === 'genealogy_researcher' ? "e.g., 'Research missing birth date for person_id: 123...'" :
                                selectedPlugin === 'odyssey_agent' ? "e.g., 'Develop a plan to create a new Frankie plugin for weather forecasting.' OR 'Research the history of AI in navigation and produce a summary report.'" :
                                "Describe the task for the selected plugin..."
                            }
                        />
                    </div>
                    {selectedPlugin === 'code_modifier' && (
                        <div>
                            <label htmlFor="targetFiles" className="block text-sm font-medium text-gray-700 mb-1">
                                <DocumentTextIcon className="h-5 w-5 inline mr-1.5 text-gray-400" />
                                Target Files (Comma-separated paths from project root)
                            </label>
                            <input type="text" id="targetFiles" value={targetFiles} onChange={(e) => setTargetFiles(e.target.value)}
                                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                                placeholder="e.g., backend/app/api/endpoints/auth.py, frontend/src/pages/Login.jsx"
                            />
                             <p className="mt-1 text-xs text-gray-500">Ensure these paths are whitelisted in 'Agent Permissions'.</p>
                        </div>
                    )}
                     {selectedPlugin === 'genealogy_researcher' && (
                        <div>
                            <label htmlFor="targetPersonId" className="block text-sm font-medium text-gray-700 mb-1">
                                <BeakerIcon className="h-5 w-5 inline mr-1.5 text-gray-400" />
                                Target Person ID (from Genealogy Module)
                            </label>
                            <input type="number" id="targetPersonId" value={targetPersonId} onChange={(e) => setTargetPersonId(e.target.value)}
                                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                                placeholder="e.g., 123 (The database ID of the person to research)"
                            />
                        </div>
                    )}
                    {formError && <p className="text-red-600 text-sm bg-red-50 p-3 rounded-md border border-red-200">{formError}</p>}
                    <div className="text-right pt-2">
                        <button type="submit" disabled={isSubmitting || !selectedPlugin || !prompt.trim()} className="inline-flex items-center justify-center py-2 px-6 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:bg-gray-400 disabled:cursor-not-allowed">
                            {isSubmitting ? 'Creating Task...' : 'Create Task'}
                        </button>
                    </div>
                </form>
            </div>

            <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200">
                <h3 className="text-lg font-semibold text-gray-700 mb-4 border-b pb-3">Task History</h3>
                {listError && <p className="text-red-600 text-sm bg-red-50 p-3 rounded-md border border-red-200 mb-4">{listError}</p>}
                <div className="overflow-x-auto">
                    <table className="min-w-full divide-y divide-gray-200">
                        <thead className="bg-gray-50">
                            <tr>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">ID</th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Plugin</th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Prompt (Excerpt)</th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider"><ClockIcon className="h-4 w-4 inline mr-1"/>Created</th>
                                <th className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-gray-200">
                            {isLoadingTasks && !tasks.length ? (
                                <tr><td colSpan="6" className="px-6 py-10 text-center text-sm text-gray-500">Loading tasks...</td></tr>
                            ) : tasks.length > 0 ? tasks.map(task => (
                                <tr key={task.id} className="hover:bg-slate-50">
                                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500 font-mono">{task.id}</td>
                                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-600 font-medium">{plugins.find(p=>p.id === task.plugin_id)?.name || task.plugin_id}</td>
                                    <td className="px-4 py-3 text-sm text-gray-800 truncate max-w-xs hover:whitespace-normal" title={task.prompt}>{task.prompt.substring(0,100)}{task.prompt.length > 100 ? '...' : ''}</td>
                                    <td className="px-4 py-3 whitespace-nowrap text-sm"><span className={getStatusPillClasses(task.status)}>{task.status}</span></td>
                                    <td className="px-4 py-3 whitespace-nowrap text-sm text-gray-500">{format(new Date(task.created_at), 'PPpp')}</td>
                                    <td className="px-4 py-3 whitespace-nowrap text-sm font-medium">
                                        <Link to={`/admin/agent/task/${task.id}`} className="text-blue-600 hover:text-blue-800 hover:underline flex items-center gap-1">
                                            <EyeIcon className="h-4 w-4"/> Review
                                        </Link>
                                    </td>
                                </tr>
                            )) : (
                                <tr>
                                    <td colSpan="6" className="px-6 py-10 text-center text-sm text-gray-500">
                                        <InboxIcon className="h-8 w-8 mx-auto text-gray-400 mb-2"/>
                                        No agent tasks found. Create one above to get started.
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

export default AgentDashboard;