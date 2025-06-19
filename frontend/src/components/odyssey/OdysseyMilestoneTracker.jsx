// frontend/src/components/odyssey/OdysseyMilestoneTracker.jsx
import React from 'react';
import { CheckCircleIcon, ClockIcon, LockClosedIcon, ChevronDownIcon, ChevronRightIcon, InformationCircleIcon, CogIcon } from '@heroicons/react/24/solid'; // Using solid for filled icons in timeline

const OdysseyMilestoneTracker = ({ plan, currentIndex, milestoneLogs = [] }) => {
    if (!plan || !plan.milestones || plan.milestones.length === 0) {
        return (
            <div className="p-3 bg-blue-50 border border-blue-200 rounded-md text-sm text-blue-700">
                <p>No milestones defined in the current plan.</p>
            </div>
        );
    }

    const getMilestoneLog = (milestoneId, index) => {
        // Try to find log by milestone_id, fallback to index if id is not reliable
        let log = milestoneLogs.find(l => l.milestone_id === milestoneId);
        if (!log && milestoneLogs[index]) { // Fallback for logs that might not have stored milestone_id correctly
            // This fallback is speculative; ideally logs always have consistent milestone_id
            // log = milestoneLogs[index];
        }
        return log;
    };

    return (
        <div className="p-4 bg-white border border-gray-300 rounded-lg shadow space-y-3">
            <h4 className="text-md font-semibold text-gray-700 flex items-center">
                <CogIcon className="h-5 w-5 mr-2 text-gray-500" />
                Milestone Progress
                <span className="ml-2 text-xs font-normal text-gray-500">
                    ({currentIndex >= 0 ? currentIndex + 1 : 0} of {plan.milestones.length} in focus/processed)
                </span>
            </h4>
            <ol className="relative border-l border-gray-200 dark:border-gray-700 ml-1">
                {plan.milestones.map((milestone, index) => {
                    const isCompleted = index < currentIndex;
                    const isCurrent = index === currentIndex;
                    const isUpcoming = index > currentIndex;
                    const logEntry = getMilestoneLog(milestone.milestone_id, index);

                    let statusIcon;
                    let statusColorClasses;

                    if (isCurrent) {
                        statusIcon = <ClockIcon className="h-5 w-5 text-white" />;
                        statusColorClasses = "bg-blue-500 ring-blue-300";
                    } else if (isCompleted) {
                        statusIcon = <CheckCircleIcon className="h-5 w-5 text-white" />;
                        statusColorClasses = logEntry?.status === 'skipped' ? "bg-yellow-500 ring-yellow-300" : "bg-green-500 ring-green-300";
                    } else { // Upcoming
                        statusIcon = <LockClosedIcon className="h-5 w-5 text-gray-700" />;
                        statusColorClasses = "bg-gray-300 ring-gray-200";
                    }

                    return (
                        <li key={milestone.milestone_id || index} className="mb-6 ml-6">
                            <span className={`absolute flex items-center justify-center w-8 h-8 rounded-full -left-4 ring-4 ring-white dark:ring-gray-900 dark:bg-blue-900 ${statusColorClasses}`}>
                                {statusIcon}
                            </span>
                            <details className="bg-gray-50 p-3 rounded-lg border border-gray-200 group" open={isCurrent || isCompleted}>
                                <summary className="font-medium text-sm text-gray-800 cursor-pointer flex justify-between items-center group-hover:text-blue-700">
                                    <span>
                                        {milestone.milestone_id ? `${milestone.milestone_id}: ` : `M${index + 1}: `}
                                        {milestone.name || "Unnamed Milestone"}
                                        {isCurrent && <span className="ml-2 text-xs text-blue-600 animate-pulse">(Current)</span>}
                                        {isCompleted && logEntry?.status === 'skipped' && <span className="ml-2 text-xs text-yellow-700">(Skipped)</span>}
                                        {isCompleted && (!logEntry || logEntry?.status !== 'skipped') && <span className="ml-2 text-xs text-green-700">(Completed)</span>}
                                    </span>
                                    <ChevronDownIcon className="h-4 w-4 text-gray-500 transform transition-transform duration-150 group-open:rotate-180" />
                                </summary>
                                <div className="mt-2 pt-2 border-t border-gray-200 text-xs text-gray-600 space-y-2"> {/* Increased space-y */}
                                    <p><strong className="text-gray-700">Description:</strong> {milestone.description || "No description."}</p>
                                    {logEntry && (
                                        <>
                                            {logEntry.tool_used && logEntry.tool_used !== "None" && (
                                                <p><strong className="text-gray-700">Tool Used:</strong> {logEntry.tool_used}</p>
                                            )}
                                            {logEntry.notes && (
                                                <p><strong className="text-gray-700">Notes:</strong> {logEntry.notes}</p>
                                            )}
                                        </>
                                    )}
                                    {!logEntry && isCompleted && (
                                        <p className="text-yellow-700 italic">Log data not available for this completed milestone.</p>
                                    )}
                                </div>
                            </details>
                        </li>
                    );
                })}
            </ol>
        </div>
    );
};

export default OdysseyMilestoneTracker;
