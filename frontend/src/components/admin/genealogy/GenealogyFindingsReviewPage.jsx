import { useState, useEffect, useCallback } from 'react';
import apiClient from '@/api/index.js';
import { 
    CheckCircleIcon, XCircleIcon, DocumentMagnifyingGlassIcon, UserCircleIcon, 
    InboxIcon, ArrowPathIcon, InformationCircleIcon 
} from '@heroicons/react/24/solid';
import { Link, useSearchParams } from 'react-router-dom';
import { format, parseISO } from 'date-fns';

// A single card for displaying and actioning a research finding
const FindingCard = ({ finding, onUpdate }) => {
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [actionError, setActionError] = useState('');

    const handleAction = async (actionType) => { // actionType: 'accept' or 'reject'
        setIsSubmitting(true);
        setActionError('');
        try {
            await apiClient.post(`/admin/findings/${finding.id}/${actionType}`);
            onUpdate(); // Trigger a refresh in the parent component
            // We don't need an alert here as the card will disappear/update, which is enough feedback.
        } catch (err) {
            const errorDetail = err.response?.data?.detail || `Failed to ${actionType} finding.`;
            setActionError(errorDetail);
            console.error(`Error ${actionType}ing finding:`, err);
        } finally {
            setIsSubmitting(false);
        }
    };

    return (
        <div className="bg-slate-50 p-4 border border-gray-200 rounded-lg shadow-sm hover:shadow-lg transition-shadow duration-150 ease-in-out">
            <div className="flex flex-col sm:flex-row justify-between items-start gap-2 mb-3 pb-3 border-b border-gray-200">
                <div>
                    <h4 className="font-semibold text-gray-800 text-md">
                        Suggested Update for: <span className="text-blue-700">{finding.data_field.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
                    </h4>
                    <p className="text-xs text-gray-500 mt-0.5">
                        Person ID: <Link to={`/genealogy/trees/${finding.person?.tree_id || 'unknown'}`} className="text-blue-500 hover:underline">{finding.person_id}</Link> 
                    </p>
                </div>
                <div className="text-sm font-semibold text-white bg-blue-500 px-2.5 py-1 rounded-full shadow-sm mt-2 sm:mt-0">
                    {finding.confidence_score}% Confidence
                </div>
            </div>
            
            {finding.llm_reasoning && (
                <div className="mt-2 mb-3 p-3 bg-indigo-50 rounded-md border border-indigo-200">
                    <strong className="text-indigo-700 text-sm block mb-1">Agent's Reasoning:</strong>
                    <p className="text-sm text-indigo-600 whitespace-pre-wrap">{finding.llm_reasoning}</p>
                </div>
            )}

            <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-sm mt-2">
                <div className="p-3 bg-red-50 border border-red-200 rounded shadow-sm">
                    <div className="font-medium text-red-700 mb-0.5">Original Value:</div>
                    <div className="text-red-600 break-words text-xs sm:text-sm">{finding.original_value || <span className="italic text-gray-500">Not Set / Empty</span>}</div>
                </div>
                <div className="p-3 bg-green-50 border border-green-200 rounded shadow-sm">
                    <div className="font-medium text-green-700 mb-0.5">Suggested Value:</div>
                    <div className="text-green-600 break-words text-xs sm:text-sm">{finding.suggested_value || <span className="italic text-gray-500">No Value Suggested</span>}</div>
                </div>
            </div>

            <div className="text-xs text-gray-500 border-t border-gray-200 pt-3 mt-3 space-y-1">
                <p><strong className="text-gray-600">Source:</strong> {finding.source_name}</p>
                {finding.source_url && 
                    <p><strong className="text-gray-600">URL:</strong> <a href={finding.source_url} target="_blank" rel="noopener noreferrer" className="text-blue-500 hover:underline break-all">{finding.source_url}</a></p>
                }
                <p className="mt-1"><strong className="text-gray-600">Citation:</strong> <span className="italic">{finding.citation_text}</span></p>
                <p className="mt-1"><strong className="text-gray-600">Finding ID:</strong> {finding.id} | <strong className="text-gray-600">Agent Task ID:</strong> {finding.agent_task_id}</p>
                 <p className="mt-1"><strong className="text-gray-600">Created:</strong> {format(parseISO(finding.created_at), 'PPpp')}</p>
            </div>

            {actionError && <p className="text-red-500 text-xs mt-2 bg-red-50 p-2 rounded">{actionError}</p>}

            {finding.status === 'UNVERIFIED' && (
                <div className="flex justify-end gap-3 pt-3 border-t border-gray-200 mt-3">
                    <button onClick={() => handleAction('reject')} disabled={isSubmitting} className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50">
                        <XCircleIcon className="h-4 w-4 text-red-500" /> Reject
                    </button>
                    <button onClick={() => handleAction('accept')} disabled={isSubmitting} className="inline-flex items-center gap-1.5 px-3 py-1.5 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50">
                        <CheckCircleIcon className="h-4 w-4" /> Accept & Apply
                    </button>
                </div>
            )}
        </div>
    );
};

// Main page for reviewing all unverified findings
const GenealogyFindingsReviewPage = () => {
    const [findingsToReview, setFindingsToReview] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [pageError, setPageError] = useState('');
    let [searchParams] = useSearchParams();
    const personIdFilter = searchParams.get('personId'); // To pre-filter if linked from person page

    const fetchUnverifiedFindings = useCallback(async (showLoadingSpinner = true) => {
        if (showLoadingSpinner) setIsLoading(true);
        setPageError('');
        try {
            // New dedicated endpoint in backend to get all unverified findings
            const response = await apiClient.get('/admin/genealogy/findings/unverified');
            setFindingsToReview(response.data);
        } catch (err) {
            setPageError('Failed to fetch unverified genealogy findings. Please ensure the backend is running and you have admin rights.');
            console.error("Fetch unverified findings error:", err);
        } finally {
            if (showLoadingSpinner) setIsLoading(false);
        }
    }, []);

    useEffect(() => {
        fetchUnverifiedFindings();
    }, [fetchUnverifiedFindings]);
    
    const filteredFindings = personIdFilter 
        ? findingsToReview.filter(f => f.person_id === parseInt(personIdFilter, 10))
        : findingsToReview;

    return (
        <div className="space-y-6">
            <header className="flex items-center justify-between pb-4 border-b border-gray-200">
                <div className="flex items-center gap-3">
                    <DocumentMagnifyingGlassIcon className="h-8 w-8 text-blue-600" />
                    <div>
                        <h2 className="text-2xl font-semibold text-gray-800">Review Genealogy Findings</h2>
                        {personIdFilter && <p className="text-sm text-gray-500">Showing findings for Person ID: {personIdFilter}</p>}
                    </div>
                </div>
                 <button onClick={() => fetchUnverifiedFindings(true)} disabled={isLoading} className="p-2 rounded-md hover:bg-gray-100 text-gray-500 disabled:text-gray-300 transition-colors" title="Refresh findings list">
                    <ArrowPathIcon className={`h-5 w-5 ${isLoading ? 'animate-spin' : ''}`} />
                </button>
            </header>
            {pageError && <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 rounded-md" role="alert"><p className="font-bold">Error</p><p>{pageError}</p></div>}
            
            <p className="text-sm text-gray-600">
                This page lists all research findings generated by the Genealogy Agent that are awaiting your review. 
                Accepting a finding will update the corresponding person's record in the database.
            </p>

            {isLoading ? (
                <div className="text-center py-20 text-gray-500"><ArrowPathIcon className="h-8 w-8 animate-spin mx-auto mb-2 text-blue-500"/>Loading findings...</div>
            ) : filteredFindings.length > 0 ? (
                <div className="space-y-6">
                    {filteredFindings.map(finding => (
                        <FindingCard key={finding.id} finding={finding} onUpdate={() => fetchUnverifiedFindings(false)} />
                    ))}
                </div>
            ) : (
                <div className="text-center py-10 bg-white p-6 rounded-lg shadow-md border border-gray-200">
                    <InboxIcon className="h-12 w-12 text-gray-400 mx-auto mb-3"/>
                    <p className="text-lg text-gray-600">No new research findings currently awaiting review.</p>
                    {personIdFilter && <p className="text-sm text-gray-500 mt-1">There are no unverified findings for this specific person.</p>}
                </div>
            )}
        </div>
    );
};

export default GenealogyFindingsReviewPage;