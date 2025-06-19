// frontend/src/components/odyssey/OdysseyTaskOrchestrator.jsx
import React from 'react';
import { getOdysseyContext, ODYSSEY_PHASES } from './odysseyUtils';
import apiClient from '@/api/index.js'; // Assuming apiClient path

// Placeholder for sub-components - will be created in later steps
import OdysseyPhaseBadge from './OdysseyPhaseBadge';
import OdysseyPlanDisplay from './OdysseyPlanDisplay';
import OdysseyMilestoneTracker from './OdysseyMilestoneTracker';
import OdysseyMilestoneReviewControls from './OdysseyMilestoneReviewControls';
import OdysseyFinalReport from './OdysseyFinalReport';

const OdysseyTaskOrchestrator = ({ task, onTaskUpdate }) => {
    if (!task || task.plugin_id !== 'odyssey_agent') {
        return null; // Only render for Odyssey tasks
    }

    const odysseyContext = getOdysseyContext(task);
    const { current_phase, plan, current_milestone_index, milestone_logs } = odysseyContext;

    const handleAdminDecision = async (decision) => {
        console.log(`Admin decision: ${decision} for task ${task.id}`);
        try {
            // Assumed API endpoint and method (PATCH to update admin_response)
            // The actual implementation of this API call might need adjustment
            // based on available backend capabilities.
            const response = await apiClient.patch(`/admin/agent/tasks/${task.id}`, {
                admin_response: decision,
            });
            if (onTaskUpdate) {
                onTaskUpdate(response.data); // Notify parent component of the updated task
            }
            console.log("Task updated with admin_response:", response.data);
        } catch (error) {
            console.error("Failed to send admin decision:", error);
            // Handle error display to user, perhaps via a toast notification
            alert(`Error submitting decision: ${error.response?.data?.detail || error.message}`);
        }
    };

    // Log current context for debugging during development
    // console.log("Odyssey Context:", odysseyContext);

    // Conditional rendering based on current_phase will be added here
    // For now, just display the phase and some context
    return (
        <div className="my-4 p-4 border border-purple-300 rounded-lg bg-purple-50 shadow-md">
            <div className="flex justify-between items-center mb-2">
                <h3 className="text-lg font-semibold text-purple-700">Odyssey Plugin Details</h3>
                <OdysseyPhaseBadge phase={current_phase} />
            </div>
            {/* The explicit "Current Phase: {text}" can be removed if the badge is deemed sufficient, or kept for clarity. */}
            {/* For now, let's comment it out to give prominence to the badge. */}
            {/* <p className="text-sm text-purple-600">Current Phase: <span className="font-bold">{current_phase || 'N/A'}</span></p> */}

            {/* Container for conditionally rendered phase-specific components */}
            <div className="mt-4 space-y-4"> {/* Increased top margin and space between children if multiple show */}
                {current_phase === ODYSSEY_PHASES.AWAITING_PLAN_REVIEW && plan && (
                    <OdysseyPlanDisplay
                        plan={plan}
                        llm_explanation={task.llm_explanation} // Pass the main task's llm_explanation
                        onDecision={handleAdminDecision}
                    />
                )}

                {/* Milestone Tracker: Displayed during execution, review, and completion phases */}
                {plan && plan.milestones && plan.milestones.length > 0 &&
                    (current_phase === ODYSSEY_PHASES.EXECUTING_MILESTONE ||
                     current_phase === ODYSSEY_PHASES.AWAITING_MILESTONE_REVIEW ||
                     current_phase === ODYSSEY_PHASES.FINALIZING ||
                     current_phase === ODYSSEY_PHASES.COMPLETED) && (
                    <OdysseyMilestoneTracker
                        plan={plan}
                        currentIndex={current_milestone_index}
                        milestoneLogs={milestone_logs}
                    />
                )}

                {current_phase === ODYSSEY_PHASES.AWAITING_MILESTONE_REVIEW && (
                    <OdysseyMilestoneReviewControls
                        llmExplanation={task.llm_explanation} // This should be explanation from the completed milestone
                        onDecision={handleAdminDecision}
                    />
                )}
                {/* {(current_phase === ODYSSEY_PHASES.EXECUTING_MILESTONE) && ( // Covered by common tracker now
                     <div className="p-3 bg-green-100 border border-green-300 rounded">Milestone Tracker UI Placeholder (Current Idx: {current_milestone_index})</div>
                )} */}
                {(current_phase === ODYSSEY_PHASES.FINALIZING || current_phase === ODYSSEY_PHASES.COMPLETED) && (
                    <OdysseyFinalReport
                        llmExplanation={task.llm_explanation}
                        milestoneLogs={milestone_logs}
                        plan={plan}
                    />
                )}
            </div>

            {/* Example of how admin decision could be triggered (for testing) */}
            {/* {current_phase === ODYSSEY_PHASES.AWAITING_PLAN_REVIEW && (
                <button onClick={() => handleAdminDecision("approve")} className="mt-2 px-3 py-1 bg-green-500 text-white rounded">Test Approve Plan</button>
            )} */}
        </div>
    );
};

export default OdysseyTaskOrchestrator;
