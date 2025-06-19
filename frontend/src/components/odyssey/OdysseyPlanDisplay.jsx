// frontend/src/components/odyssey/OdysseyPlanDisplay.jsx
import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { DocumentTextIcon, LightBulbIcon, QuestionMarkCircleIcon, CheckCircleIcon, ArrowPathIcon, XCircleIcon } from '@heroicons/react/24/outline';

const OdysseyPlanDisplay = ({ plan, llm_explanation, onDecision }) => {
    if (!plan) {
        return (
            <div className="p-4 bg-yellow-50 border border-yellow-300 rounded-md text-yellow-700">
                <p>No plan details available to display. Waiting for plan generation...</p>
            </div>
        );
    }

    const { project_title, milestones = [], clarifying_questions = [] } = plan;

    // The llm_explanation from the backend's PLANNING phase should contain the overall_summary.
    // We'll display it directly.
    const overall_summary_and_questions_markdown = llm_explanation || "_No summary or clarifying questions provided by the planning phase._";

    return (
        <div className="p-4 bg-white border border-gray-300 rounded-lg shadow space-y-6">
            <header className="pb-4 border-b border-gray-200">
                <h4 className="text-xl font-semibold text-gray-800 flex items-center">
                    <DocumentTextIcon className="h-6 w-6 mr-2 text-purple-600" />
                    Proposed Project Plan: {project_title || "Untitled Plan"}
                </h4>
            </header>

            <section>
                <h5 className="text-md font-semibold text-gray-700 mb-2 flex items-center">
                    <LightBulbIcon className="h-5 w-5 mr-2 text-yellow-500" />
                    Plan Overview & Clarifications
                </h5>
                <div className="prose prose-sm max-w-none p-3 border border-gray-200 rounded-md bg-slate-50 text-gray-800">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {overall_summary_and_questions_markdown}
                    </ReactMarkdown>
                </div>
            </section>

            {milestones && milestones.length > 0 && (
                <section>
                    <h5 className="text-md font-semibold text-gray-700 mb-3">Milestones ({milestones.length}):</h5>
                    <div className="space-y-4 pl-4"> {/* Increased pl from 2 to 4, space-y to 4 for consistency */}
                        {milestones.map((milestone, index) => (
                            <details key={milestone.milestone_id || index} className="p-3 border border-gray-200 rounded-md bg-gray-50 hover:bg-gray-100 transition-colors duration-150 group">
                                <summary className="font-medium text-sm text-gray-700 cursor-pointer group-hover:text-purple-700 flex justify-between items-center"> {/* Added flex for icon alignment */}
                                    {milestone.milestone_id ? `${milestone.milestone_id}: ` : `M${index + 1}: `} {milestone.name || "Unnamed Milestone"}
                                    <span className="text-xs text-gray-500 ml-2 group-hover:text-purple-600">({milestone.estimated_sub_steps?.length || 0} sub-steps)</span>
                                    {/* Chevron for details, ideally part of the summary text flow or aligned right if summary text is grouped */}
                                </summary>
                                <div className="mt-2 pt-2 border-t border-gray-200 text-xs text-gray-600 space-y-2"> {/* Increased space-y for content */}
                                    <p><strong className="text-gray-700">Description:</strong> {milestone.description || "No description."}</p>
                                    {milestone.estimated_sub_steps && milestone.estimated_sub_steps.length > 0 && (
                                        <div>
                                            <strong className="text-gray-700">Sub-steps:</strong>
                                            <ul className="list-disc pl-5 mt-1">
                                                {milestone.estimated_sub_steps.map((step, stepIdx) => (
                                                    <li key={stepIdx}>{step}</li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                    {milestone.potential_tools && milestone.potential_tools.length > 0 && (
                                         <p><strong className="text-gray-700">Potential Tools:</strong> {milestone.potential_tools.join(', ')}</p>
                                    )}
                                </div>
                            </details>
                        ))}
                    </div>
                </section>
            )}

            <footer className="pt-6 border-t border-gray-200 flex flex-col sm:flex-row justify-end items-center gap-3">
                <button
                    onClick={() => onDecision("replan")}
                    className="w-full sm:w-auto py-2 px-4 border border-yellow-400 text-yellow-700 bg-yellow-50 hover:bg-yellow-100 rounded-md shadow-sm text-sm font-medium flex items-center justify-center gap-2 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-500"
                >
                    <ArrowPathIcon className="h-4 w-4" /> Request Replan
                </button>
                <button
                    onClick={() => onDecision("stop")}
                    className="w-full sm:w-auto py-2 px-4 border border-red-400 text-red-700 bg-red-50 hover:bg-red-100 rounded-md shadow-sm text-sm font-medium flex items-center justify-center gap-2 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
                >
                    <XCircleIcon className="h-4 w-4" /> Cancel Task
                </button>
                <button
                    onClick={() => onDecision("approve")}
                    className="w-full sm:w-auto py-2 px-4 border border-transparent text-white bg-green-600 hover:bg-green-700 rounded-md shadow-sm text-sm font-medium flex items-center justify-center gap-2 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                >
                    <CheckCircleIcon className="h-4 w-4" /> Approve Plan
                </button>
            </footer>
        </div>
    );
};

export default OdysseyPlanDisplay;
