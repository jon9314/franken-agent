// frontend/src/components/odyssey/OdysseyFinalReport.jsx
import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ClipboardDocumentCheckIcon } from '@heroicons/react/24/solid';

const OdysseyFinalReport = ({ llmExplanation, milestoneLogs, plan }) => {
    // The llmExplanation from _phase_finalizing is expected to be comprehensive,
    // potentially already including a summary derived from milestone_logs.
    // This component will primarily render that explanation.
    // It can act as a fallback or supplement if needed, but the backend should do the heavy lifting.

    const projectTitle = plan?.project_title || "Task";

    let finalReportMarkdown = llmExplanation;

    if (!finalReportMarkdown) {
        // Fallback if backend explanation is somehow missing
        let report = `## Task Finalized: ${projectTitle}\n\n`;
        report += "The task has been marked as complete.\n\n";
        if (milestoneLogs && milestoneLogs.length > 0) {
            report += `**Summary of Processed Milestones (${milestoneLogs.length} total):**\n\n`;
            milestoneLogs.forEach(log => {
                report += `- **${log.name || 'N/A'}** (ID: ${log.milestone_id || 'N/A'}): Status: ${log.status || 'N/A'}. Tool Used: ${log.tool_used || 'None'}.\n`;
            });
        } else {
            report += "No detailed milestone logs were recorded for this task.\n";
        }
        finalReportMarkdown = report;
    }

    return (
        <div className="p-4 bg-white border border-gray-300 rounded-lg shadow space-y-4">
            <h4 className="text-xl font-semibold text-gray-800 flex items-center">
                <ClipboardDocumentCheckIcon className="h-6 w-6 mr-2 text-green-600" />
                Final Task Report: {projectTitle}
            </h4>

            <div className="prose prose-sm max-w-none p-3 border border-gray-200 rounded-md bg-slate-50 text-gray-800">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {finalReportMarkdown}
                </ReactMarkdown>
            </div>

            {/* Optional: Raw milestone logs for debugging or if not fully in llmExplanation */}
            {/*
            {milestoneLogs && milestoneLogs.length > 0 && (
                <details className="mt-2 text-xs">
                    <summary className="cursor-pointer text-gray-500 hover:text-gray-700">View Raw Milestone Logs ({milestoneLogs.length})</summary>
                    <pre className="mt-1 p-2 bg-gray-100 border border-gray-200 rounded overflow-x-auto">
                        {JSON.stringify(milestoneLogs, null, 2)}
                    </pre>
                </details>
            )}
            */}
        </div>
    );
};

export default OdysseyFinalReport;
