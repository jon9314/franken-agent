// frontend/src/components/odyssey/odysseyUtils.js

/**
 * Parses task_context_data for Odyssey tasks and provides default values.
 * @param {object} task - The agent task object.
 * @returns {object} Parsed context with defaults.
 */
export const getOdysseyContext = (task) => {
    let contextData = {};
    if (task && task.task_context_data) {
        try {
            if (typeof task.task_context_data === 'string') {
                contextData = JSON.parse(task.task_context_data);
            } else {
                contextData = task.task_context_data; // Assume already an object
            }
        } catch (error) {
            console.error("Error parsing task_context_data:", error);
            // Return default structure on error to prevent UI crashes
        }
    }

    return {
        current_phase: contextData.current_phase || null,
        plan: contextData.plan || null, // { project_title, overall_summary, clarifying_questions, milestones }
        current_milestone_index: typeof contextData.current_milestone_index === 'number' ? contextData.current_milestone_index : -1,
        milestone_logs: contextData.milestone_logs || [],
    };
};

// Define phase constants for easier use in components
export const ODYSSEY_PHASES = {
    PLANNING: "PLANNING",
    AWAITING_PLAN_REVIEW: "AWAITING_PLAN_REVIEW",
    EXECUTING_MILESTONE: "EXECUTING_MILESTONE",
    AWAITING_MILESTONE_REVIEW: "AWAITING_MILESTONE_REVIEW",
    FINALIZING: "FINALIZING",
    COMPLETED: "COMPLETED",
};
