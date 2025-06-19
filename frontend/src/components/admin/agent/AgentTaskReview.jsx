import { useState, useEffect, useCallback } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import apiClient from '@/api/index.js';
import OdysseyTaskOrchestrator from '@/components/odyssey/OdysseyTaskOrchestrator';
import ReactDiffViewer, { DiffMethod } from 'react-diff-viewer-continued';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { 
    CheckCircleIcon, XCircleIcon, BeakerIcon, InformationCircleIcon, 
    ArrowUturnLeftIcon, LightBulbIcon, DocumentTextIcon, PaintBrushIcon, CpuChipIcon, ClockIcon,
    ExclamationTriangleIcon, ArrowPathIcon, HashtagIcon, UserCircleIcon,
    ClipboardDocumentListIcon
} from '@heroicons/react/24/solid';
import { format, parseISO } from 'date-fns';
import { getOdysseyContext, ODYSSEY_PHASES } from '@/components/odyssey/odysseyUtils'; // Import ODYSSEY_PHASES and getOdysseyContext
import OdysseyPhaseBadge from '@/components/odyssey/OdysseyPhaseBadge'; // Import OdysseyPhaseBadge

const getStatusPillClasses = (status) => {
    const base = "px-2.5 py-1 text-xs font-semibold rounded-full inline-block leading-tight";
    switch (status) {
        case 'PENDING': return `${base} bg-slate-200 text-slate-800`;
        case 'PLANNING': case 'ANALYZING': case 'TESTING': case 'EXECUTING_MILESTONE': return `${base} bg-yellow-200 text-yellow-800 animate-pulse`;
        case 'AWAITING_REVIEW': return `${base} bg-blue-200 text-blue-800`;
        case 'APPLIED': return `${base} bg-green-200 text-green-800`;
        case 'REJECTED': return `${base} bg-pink-200 text-pink-800`;
        case 'ERROR': return `${base} bg-red-200 text-red-800`;
        default: return `${base} bg-gray-200 text-gray-800`;
    }
};

const TestResultPanel = ({ status, results }) => {
    const [isExpanded, setIsExpanded] = useState(status === 'FAIL');
    const getStatusInfo = () => {
        switch (status) {
            case 'PASS': return { icon: <CheckCircleIcon className="h-6 w-6 text-green-600" />, title: 'Tests Passed', color: 'green'};
            case 'FAIL': return { icon: <XCircleIcon className="h-6 w-6 text-red-600" />, title: 'Tests Failed', color: 'red'};
            default: return { icon: <BeakerIcon className="h-6 w-6 text-gray-500" />, title: 'Tests Not Run', color: 'gray'};
        }
    };
    const { icon, title, color } = getStatusInfo();
    const baseBorderColor = color === 'gray' ? 'border-gray-300' : `border-${color}-400`;
    const baseBgColor = color === 'gray' ? 'bg-gray-50' : `bg-${color}-50`;
    const baseTextColor = color === 'gray' ? 'text-gray-700' : `text-${color}-800`;

    return (
        <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200">
            <div className={`p-4 rounded-t-lg border-l-4 ${baseBgColor} ${baseBorderColor}`}>
                <div className="flex items-center justify-between">
                    <div className="flex items-center">{icon}<h3 className={`ml-3 text-lg font-semibold ${baseTextColor}`}>{title}</h3></div>
                    {results && (<button onClick={() => setIsExpanded(!isExpanded)} className="text-sm text-blue-600 hover:underline"> {isExpanded ? 'Hide Details' : 'Show Details'} </button>)}
                </div>
            </div>
            {isExpanded && results && (
                <div className="p-4 bg-slate-800 text-slate-100 rounded-b-lg overflow-x-auto max-h-96 border border-t-0 border-gray-300">
                    <pre className="text-xs whitespace-pre-wrap break-all"><code>{results}</code></pre>
                </div>
            )}
        </div>
    );
};

const AgentTaskReview = () => {
    const { taskId } = useParams();
    const [task, setTask] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [pageError, setPageError] = useState('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [overrideTestFailures, setOverrideTestFailures] = useState(false);

    const fetchTaskDetails = useCallback(async () => {
        setIsLoading(true); setPageError('');
        try {
            const response = await apiClient.get(`/admin/agent/tasks/${taskId}`);
            setTask(response.data);
        } catch (err) { setPageError('Failed to fetch task details.'); console.error(err); } 
        finally { setIsLoading(false); }
    }, [taskId]);

    useEffect(() => { fetchTaskDetails(); }, [fetchTaskDetails]);

    const handleApproval = async () => {
        let confirmMsg = "Are you sure you want to approve this stage and proceed?";
        if (task?.plugin_id === "code_modifier" && task?.test_status === 'FAIL' && !overrideTestFailures) {
            if (!window.confirm("WARNING: Automated tests failed. Are you sure you want to override and approve?")) return;
        } else if (!window.confirm(confirmMsg)) return;

        setIsSubmitting(true); setPageError('');
        try {
            const response = await apiClient.post(`/admin/agent/tasks/${taskId}/approve`);
            setTask(response.data);
            alert(`Task #${taskId} has been approved. The agent will proceed to the next step or finalize.`);
        } catch (err) {
            const errorDetail = err.response?.data?.detail || 'Server error during approval.';
            setPageError(errorDetail); alert(`Failed to approve task: ${errorDetail}`);
        } finally { setIsSubmitting(false); }
    };
    
    if (isLoading) return <div className="text-center py-20"><ArrowPathIcon className="h-8 w-8 animate-spin mx-auto text-blue-500 mb-2"/>Loading task details...</div>;
    if (pageError) return <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-6 rounded-md" role="alert"><p className="font-bold">Error</p><p>{pageError}</p><Link to="/admin/agent" className="text-blue-600 hover:underline mt-2 block">Return to Dashboard</Link></div>;
    if (!task) return <div className="text-center py-20 text-gray-600">Task not found. <Link to="/admin/agent" className="text-blue-600 hover:underline">Return to Dashboard</Link></div>;

    const canApproveTask = task.status === 'AWAITING_REVIEW';
    const approvalButtonDisabled = !canApproveTask || isSubmitting || (task.plugin_id === "code_modifier" && task.test_status === 'FAIL' && !overrideTestFailures);

    let approveButtonText = "Approve & Apply";
    if (task.plugin_id === 'odyssey_agent' && task.task_context_data) {
        try {
            const context = JSON.parse(task.task_context_data);
            if (context.current_phase === 'AWAITING_PLAN_REVIEW') approveButtonText = "Approve Plan & Proceed";
            else if (context.current_phase === 'AWAITING_MILESTONE_REVIEW') approveButtonText = "Approve Milestone & Continue";
            else if (context.current_phase === 'AWAITING_FINAL_REVIEW') approveButtonText = "Complete Task";
        } catch (e) { console.error("Error parsing task context for button text", e); }
    }

    let odysseyPhase = null;
    if (task && task.plugin_id === 'odyssey_agent') {
        const odysseyContext = getOdysseyContext(task);
        odysseyPhase = odysseyContext.current_phase;
    }

    return (
        <div className="space-y-6 pb-10">
            <nav className="flex items-center justify-between pb-4 border-b border-gray-200">
                <Link to="/admin/agent" className="inline-flex items-center text-sm text-blue-600 hover:text-blue-800 hover:underline"><ArrowUturnLeftIcon className="h-4 w-4 mr-1.5"/> Back to Agent Dashboard</Link>
                <button onClick={fetchTaskDetails} disabled={isLoading} className="p-1.5 rounded-md hover:bg-gray-100 text-gray-400 hover:text-gray-600 disabled:text-gray-300" title="Refresh task details"><ArrowPathIcon className={`h-5 w-5 ${isLoading ? 'animate-spin': ''}`}/></button>
            </nav>
            
            <header className="bg-white p-6 rounded-lg shadow-md border border-gray-200">
                <div className="flex flex-col sm:flex-row justify-between sm:items-center gap-2">
                    <h2 className="text-xl sm:text-2xl font-bold text-gray-800">Review Agent Task <span className="font-mono text-blue-600">#{task.id}</span></h2>
                    <div className="flex items-center gap-2"> {/* Wrapper for statuses */}
                        {odysseyPhase && (
                            <OdysseyPhaseBadge phase={odysseyPhase} />
                        )}
                        <span className={getStatusPillClasses(task.status)}>{task.status}</span>
                    </div>
                </div>
                <div className="mt-3 text-xs text-gray-500 space-y-0.5">
                    <p className="flex items-center"><UserCircleIcon className="h-4 w-4 mr-1.5"/>Owner ID: {task.owner_id}</p>
                    <p className="flex items-center"><CpuChipIcon className="h-4 w-4 mr-1.5"/>Plugin: <span className="font-medium text-gray-700">{task.plugin_id}</span></p>
                    <p className="flex items-center"><ClockIcon className="h-4 w-4 mr-1.5"/>Created: {format(parseISO(task.created_at), 'PPpp')}</p>
                    {task.updated_at && <p className="flex items-center"><ClockIcon className="h-4 w-4 mr-1.5"/>Updated: {format(parseISO(task.updated_at), 'PPpp')}</p>}
                </div>
            </header>

            <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200 space-y-3">
                <h3 className="font-semibold text-gray-800 flex items-center mb-1"><LightBulbIcon className="h-5 w-5 mr-2 text-yellow-500"/>Original Prompt</h3>
                <p className="p-3 bg-slate-50 border border-slate-200 rounded-md text-gray-700 text-sm whitespace-pre-wrap">{task.prompt}</p>
            </div>
            
            {task.llm_explanation && (
                <div className="bg-white p-6 rounded-lg shadow-md border border-gray-200">
                    <h3 className="text-xl font-semibold text-gray-700 mb-3 flex items-center">
                        {task.plugin_id === 'odyssey_agent' ? <ClipboardDocumentListIcon className="h-6 w-6 mr-2 text-purple-600"/> : <InformationCircleIcon className="h-5 w-5 mr-2 text-blue-500"/>}
                        Agent's Plan & Explanation
                    </h3>
                    <div className="prose prose-sm max-w-none p-3 border border-gray-200 rounded-md bg-slate-50 text-gray-800">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{task.llm_explanation}</ReactMarkdown>
                    </div>
                </div>
            )}

            {/* Odyssey Plugin Specific UI */}
            {task.plugin_id === 'odyssey_agent' && (
                <OdysseyTaskOrchestrator task={task} onTaskUpdate={setTask} />
            )}
            
            {task.plugin_id === "code_modifier" && (
                <>
                    <div className="bg-blue-50 border-l-4 border-blue-400 p-4 rounded-r-md shadow-sm">
                        <div className="flex"><div className="flex-shrink-0"><PaintBrushIcon className="h-5 w-5 text-blue-500" aria-hidden="true" /></div><div className="ml-3"><p className="text-sm text-blue-700">Proposed code changes have been automatically formatted using Black & Prettier.</p></div></div>
                    </div>
                    {task.test_status !== 'NOT_RUN' && (<TestResultPanel status={task.test_status} results={task.test_results} />)}
                    {task.proposed_diff && task.proposed_diff.trim() && !task.proposed_diff.startsWith("-- No changes") && (
                        <div className="bg-white rounded-lg shadow-md overflow-hidden border border-gray-200">
                            <h3 className="text-xl font-semibold text-gray-700 p-6">Proposed Code Changes (Diff)</h3>
                            <div className="border-t border-gray-200 text-sm">
                                <ReactDiffViewer oldValue={""} newValue={task.proposed_diff} splitView={true} useDarkTheme={false} showDiffOnly={false} compareMethod={DiffMethod.WORDS_WITH_SPACE}/>
                            </div>
                        </div>
                    )}
                </>
            )}

            {task.status === 'AWAITING_REVIEW' && (
                <div className="bg-white p-6 rounded-lg shadow-md mt-6 border border-gray-200 space-y-4">
                     {task.plugin_id === "code_modifier" && task.test_status === 'FAIL' && (
                        <div className="border border-yellow-400 bg-yellow-50 p-4 rounded-md">
                            <div className="flex items-start"><ExclamationTriangleIcon className="h-6 w-6 text-yellow-600 mr-3 flex-shrink-0" />
                                <div>
                                    <h4 className="font-semibold text-yellow-800">Tests Failed!</h4>
                                    <p className="text-sm text-yellow-700 mt-1">Automated tests failed. Review the test output carefully. You can override this if you are certain the changes are safe.</p>
                                    <div className="mt-3 flex items-center">
                                        <input id="overrideTestFailures" type="checkbox" checked={overrideTestFailures} onChange={(e) => setOverrideTestFailures(e.target.checked)} className="h-4 w-4 text-red-600 border-gray-300 rounded focus:ring-red-500"/>
                                        <label htmlFor="overrideTestFailures" className="ml-2 block text-sm text-red-700 font-medium">I understand the risks and wish to approve despite failed tests.</label>
                                    </div>
                                </div>
                            </div>
                        </div>
                    )}
                    <div className="flex flex-col sm:flex-row justify-end items-center gap-3 pt-4 border-t border-gray-200">
                        <button onClick={() => alert("Reject/Revise action to be implemented.")} disabled={isSubmitting} className="w-full sm:w-auto py-2 px-5 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-60">Reject / Request Revision</button>
                        {/* The main approval button is hidden if OdysseyTaskOrchestrator is expected to provide specific review actions */}
                        {!(task.plugin_id === 'odyssey_agent' && task.task_context_data &&
                          (JSON.parse(task.task_context_data).current_phase === ODYSSEY_PHASES.AWAITING_PLAN_REVIEW ||
                           JSON.parse(task.task_context_data).current_phase === ODYSSEY_PHASES.AWAITING_MILESTONE_REVIEW)) &&
                          <button onClick={handleApproval} disabled={approvalButtonDisabled} className="w-full sm:w-auto py-2 px-5 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:bg-gray-400 disabled:cursor-not-allowed">{isSubmitting ? 'Processing...' : approveButtonText}</button>
                        }
                    </div>
                </div>
            )}
            
            {task.status === 'APPLIED' && ( <div className="bg-green-50 border-l-4 border-green-500 p-4 rounded-r-md mt-6 shadow-sm">...</div> )}
            {task.status === 'REJECTED' && ( <div className="bg-pink-50 border-l-4 border-pink-500 p-4 rounded-r-md mt-6 shadow-sm">...</div> )}
            {task.status === 'ERROR' && task.error_message && ( <div className="bg-red-50 border-l-4 border-red-500 p-4 rounded-r-md mt-6 shadow-sm">...</div> )}
        </div>
    );
};

export default AgentTaskReview;