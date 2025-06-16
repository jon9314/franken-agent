import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import apiClient from '@/api/index.js';
import { 
    BeakerIcon, UsersIcon, ArrowUturnLeftIcon, InboxIcon, 
    MagnifyingGlassIcon, DocumentMagnifyingGlassIcon, ArrowPathIcon 
} from '@heroicons/react/24/solid';
import { format } from 'date-fns';
import useAuth from '@/hooks/useAuth';

// PersonRow Component: Renders a single row in the individuals table
const PersonRow = ({ person, treeId }) => {
    const [isResearching, setIsResearching] = useState(false);
    const [researchMessage, setResearchMessage] = useState('');
    const { auth } = useAuth(); // Check for admin role
    const messageTimeoutRef = useRef(null);

    const handleResearchClick = async () => {
        if (!window.confirm(`This will create an agent task to research missing information for ${person.first_name || ''} ${person.last_name || ''} (ID: ${person.id}).\n\nThis action requires admin privileges. Are you sure you want to proceed?`)) return;
        
        setIsResearching(true);
        setResearchMessage('Research task is being initiated...');
        if(messageTimeoutRef.current) clearTimeout(messageTimeoutRef.current);

        try {
            const taskData = {
                plugin_id: 'genealogy_researcher',
                prompt: `Research missing genealogical information for person: ${person.first_name || ''} ${person.last_name || ''} (Person ID: ${person.id}, from Tree ID: ${treeId}).`,
                target_person_id: person.id,
                target_tree_id: parseInt(treeId, 10),
            };
            await apiClient.post('/admin/agent/tasks', taskData);
            setResearchMessage("Success! Monitor progress in Admin Panel > Agent Tasks.");
        } catch (err) {
            const errorDetail = err.response?.data?.detail || "Failed to start research task. You may need admin privileges.";
            setResearchMessage(`Error: ${errorDetail}`);
            console.error("Research task initiation error:", err);
        } finally {
            setIsResearching(false);
            // Clear the message after a few seconds
            messageTimeoutRef.current = setTimeout(() => {
                setResearchMessage('');
            }, 8000); // 8 seconds
        }
    };
    
    // Cleanup timeout on component unmount
    useEffect(() => {
        return () => {
            if (messageTimeoutRef.current) clearTimeout(messageTimeoutRef.current);
        };
    }, []);

    return (
        <tr className="hover:bg-slate-50 transition-colors">
            <td className="px-5 py-3 whitespace-nowrap text-sm font-medium text-gray-800">
                {person.first_name || <span className="italic text-gray-400">Unknown</span>} {person.last_name || ''}
                <span className="block text-xs text-gray-500">GEDCOM ID: {person.gedcom_id} (DB ID: {person.id})</span>
            </td>
            <td className="px-5 py-3 whitespace-nowrap text-sm text-gray-600">{person.sex || <span className="italic text-gray-400">N/A</span>}</td>
            <td className="px-5 py-3 whitespace-nowrap text-sm text-gray-600">{person.birth_date || <span className="italic text-gray-400">N/A</span>}</td>
            <td className="px-5 py-3 whitespace-nowrap text-sm text-gray-600">{person.death_date || <span className="italic text-gray-400">N/A</span>}</td>
            <td className="px-5 py-3 whitespace-nowrap text-right text-sm font-medium">
                {auth.user?.role === 'admin' && (
                    <div className="flex items-center justify-end gap-2 relative group">
                        <button 
                            onClick={handleResearchClick} 
                            disabled={isResearching} 
                            className="inline-flex items-center gap-1.5 text-xs py-1 px-2.5 border border-blue-500 text-blue-600 hover:bg-blue-50 rounded-md disabled:text-gray-400 disabled:border-gray-300 disabled:cursor-not-allowed transition-colors"
                            title="Initiate AI research for this person (Admin only)"
                        >
                            <BeakerIcon className={`h-4 w-4 ${isResearching ? 'animate-spin' : ''}`} />
                            {isResearching ? 'Starting...' : 'Research'}
                        </button>
                        {researchMessage && <p className={`absolute right-0 top-full mt-1 w-64 p-2 text-xs rounded shadow-lg z-10 ${researchMessage.startsWith('Error:') ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'}`}>{researchMessage}</p>}
                        
                        <Link 
                            to={`/admin/genealogy-review?personId=${person.id}`}
                            className="inline-flex items-center gap-1.5 text-xs py-1 px-2.5 border border-gray-300 text-gray-700 hover:bg-gray-100 rounded-md transition-colors"
                            title="Review research findings for this person (Admin Panel)"
                        >
                            <DocumentMagnifyingGlassIcon className="h-4 w-4"/>
                            Review Findings
                        </Link>
                    </div>
                )}
                 {auth.user?.role !== 'admin' && (
                     <p className="text-xs text-gray-400 italic">Admin required to run research.</p>
                 )}
            </td>
        </tr>
    );
};

// Main Page Component for viewing a single Family Tree
const FamilyTreeDetailPage = () => {
    const { treeId } = useParams();
    const [tree, setTree] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [pageError, setPageError] = useState('');
    const [searchTerm, setSearchTerm] = useState('');

    const fetchTreeDetails = useCallback(async (showLoadingSpinner = true) => {
        if(showLoadingSpinner) setIsLoading(true);
        setPageError('');
        try {
            const response = await apiClient.get(`/genealogy/trees/${treeId}`);
            setTree(response.data);
        } catch (err) {
            setPageError('Failed to load family tree details. The tree might not exist or you may not have permission.');
            console.error("Failed to fetch tree details for ID " + treeId + ":", err);
        } finally {
            if(showLoadingSpinner) setIsLoading(false);
        }
    }, [treeId]);

    useEffect(() => {
        fetchTreeDetails();
    }, [fetchTreeDetails]);

    const filteredPersons = useMemo(() => {
        if (!tree?.persons) return [];
        return tree.persons.filter(person => {
            const fullName = `${person.first_name || ''} ${person.last_name || ''}`.toLowerCase();
            const gedcomId = (person.gedcom_id || '').toLowerCase();
            const dbId = String(person.id);
            const term = searchTerm.toLowerCase();
            return fullName.includes(term) || gedcomId.includes(term) || dbId.includes(term);
        });
    }, [tree?.persons, searchTerm]);

    if (isLoading) return <div className="text-center py-20"><ArrowPathIcon className="h-8 w-8 animate-spin mx-auto text-blue-500 mb-2"/>Loading family tree details...</div>;
    if (pageError) return <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-6 rounded-md" role="alert"><p className="font-bold">Error</p><p>{pageError}</p> <Link to="/genealogy" className="text-blue-600 hover:underline mt-2 block">Return to Genealogy Dashboard</Link></div>;
    if (!tree) return <div className="text-center py-20 text-gray-600">Family tree not found. <Link to="/genealogy" className="text-blue-600 hover:underline">Return to Genealogy Dashboard</Link></div>;

    return (
        <div className="space-y-6">
            <nav className="flex items-center justify-between pb-4 border-b border-gray-200">
                <Link to="/genealogy" className="inline-flex items-center text-sm text-blue-600 hover:text-blue-800 hover:underline">
                    <ArrowUturnLeftIcon className="h-4 w-4 mr-1.5"/> Back to Genealogy Dashboard
                </Link>
                <button onClick={() => fetchTreeDetails(true)} disabled={isLoading} className="p-1.5 rounded-md hover:bg-gray-100 text-gray-400 hover:text-gray-600 disabled:text-gray-300" title="Refresh tree details">
                    <ArrowPathIcon className={`h-5 w-5 ${isLoading ? 'animate-spin': ''}`}/>
                </button>
            </nav>
            
            <header className="bg-white p-6 rounded-lg shadow-md border border-gray-200">
                <h1 className="text-2xl sm:text-3xl font-bold text-gray-800">{tree.file_name}</h1>
                <p className="text-sm text-gray-500 mt-1">
                    Uploaded on {format(new Date(tree.created_at), 'PPPP')} | Contains <span className="font-semibold">{tree.persons.length}</span> individuals and <span className="font-semibold">{tree.families.length}</span> families.
                </p>
            </header>
            
            <div className="bg-white shadow-md overflow-hidden sm:rounded-lg border border-gray-200">
                <div className="px-4 py-4 sm:px-6 border-b border-gray-200">
                    <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
                         <h3 className="text-xl leading-6 font-medium text-gray-900 flex items-center">
                            <UsersIcon className="h-6 w-6 mr-2 text-blue-600"/> Individuals ({filteredPersons.length} of {tree.persons.length})
                        </h3>
                        <div className="relative w-full sm:w-auto">
                            <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"><MagnifyingGlassIcon className="h-5 w-5 text-gray-400" aria-hidden="true" /></div>
                            <input type="search" placeholder="Search by name or ID..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="block w-full sm:w-72 pl-10 pr-3 py-2 border border-gray-300 rounded-md shadow-sm leading-5 bg-white placeholder-gray-500 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"/>
                        </div>
                    </div>
                </div>
                <div className="overflow-x-auto">
                    {filteredPersons.length > 0 ? (
                        <table className="min-w-full divide-y divide-gray-200">
                            <thead className="bg-gray-50">
                                <tr>
                                    <th scope="col" className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Name & ID</th>
                                    <th scope="col" className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Sex</th>
                                    <th scope="col" className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Birth Date</th>
                                    <th scope="col" className="px-5 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Death Date</th>
                                    <th scope="col" className="relative px-5 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">Admin Actions</th>
                                </tr>
                            </thead>
                            <tbody className="bg-white divide-y divide-gray-200">
                                {filteredPersons.map(person => <PersonRow key={person.id} person={person} treeId={tree.id} />)}
                            </tbody>
                        </table>
                    ) : (
                         <div className="text-center py-10 px-4">
                            <InboxIcon className="h-10 w-10 text-gray-400 mx-auto mb-2"/>
                            <p className="text-md text-gray-600">{tree.persons.length === 0 ? "No individuals found in this family tree." : "No individuals found matching your search."}</p>
                         </div>
                    )}
                </div>
                 {filteredPersons.length > 0 && (
                     <div className="px-4 py-3 bg-gray-50 border-t border-gray-200 text-xs text-gray-500">Displaying {filteredPersons.length} of {tree.persons.length} total individuals.</div>
                 )}
            </div>
        </div>
    );
};

export default FamilyTreeDetailPage;