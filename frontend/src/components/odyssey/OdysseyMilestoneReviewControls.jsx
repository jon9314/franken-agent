// frontend/src/components/odyssey/OdysseyMilestoneReviewControls.jsx
import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { CheckCircleIcon, ArrowPathIcon, XCircleIcon, ChevronRightIcon, LightBulbIcon } from '@heroicons/react/24/outline'; // Using outline for buttons

const OdysseyMilestoneReviewControls = ({ llmExplanation, onDecision }) => {
    return (
        <div className="p-4 bg-white border border-gray-300 rounded-lg shadow space-y-4">
            <h4 className="text-md font-semibold text-gray-700 flex items-center">
                <LightBulbIcon className="h-5 w-5 mr-2 text-blue-500" />
                Milestone Review & Action
            </h4>

            {llmExplanation && (
                <div className="prose prose-sm max-w-none p-3 border border-gray-200 rounded-md bg-slate-50 text-gray-800">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{llmExplanation}</ReactMarkdown>
                </div>
            )}
            {!llmExplanation && (
                <p className="text-sm text-gray-600 italic">No additional explanation provided for this milestone review.</p>
            )}

            <div className="pt-4 border-t border-gray-200 grid grid-cols-2 sm:grid-cols-4 gap-3">
                <button
                    onClick={() => onDecision("approve")}
                    title="Approve this milestone and proceed to the next one, or to finalization if this was the last."
                    className="w-full py-2 px-3 border border-transparent text-white bg-green-600 hover:bg-green-700 rounded-md shadow-sm text-sm font-medium flex items-center justify-center gap-2 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500"
                >
                    <CheckCircleIcon className="h-4 w-4" /> Approve {/* Icon size to h-4 w-4 */}
                </button>
                <button
                    onClick={() => onDecision("skip")}
                    title="Skip executing the next planned milestone and move to the one after that, or to finalization if skipping the last."
                    className="w-full py-2 px-3 border border-yellow-500 text-yellow-700 bg-yellow-100 hover:bg-yellow-200 rounded-md shadow-sm text-sm font-medium flex items-center justify-center gap-2 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-600"
                >
                    <ChevronRightIcon className="h-4 w-4" /> Skip Next {/* Icon size to h-4 w-4 */}
                </button>
                <button
                    onClick={() => onDecision("replan")}
                    title="Discard the current plan and return to the planning phase to generate a new plan."
                    className="w-full py-2 px-3 border border-blue-500 text-blue-700 bg-blue-100 hover:bg-blue-200 rounded-md shadow-sm text-sm font-medium flex items-center justify-center gap-2 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-600"
                >
                    <ArrowPathIcon className="h-4 w-4" /> Replan Task {/* Icon size to h-4 w-4 */}
                </button>
                <button
                    onClick={() => onDecision("stop")}
                    title="Halt the task completely. No further milestones will be executed."
                    className="w-full py-2 px-3 border border-red-500 text-red-700 bg-red-100 hover:bg-red-200 rounded-md shadow-sm text-sm font-medium flex items-center justify-center gap-2 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-600"
                >
                    <XCircleIcon className="h-4 w-4" /> Cancel Task {/* Icon size to h-4 w-4 */}
                </button>
            </div>
        </div>
    );
};

export default OdysseyMilestoneReviewControls;
