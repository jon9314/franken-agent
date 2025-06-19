// frontend/src/components/odyssey/OdysseyPhaseBadge.jsx
import React from 'react';
import { ODYSSEY_PHASES } from './odysseyUtils'; // Assuming this path is correct

const getOdysseyPhasePillClasses = (phase) => {
    const base = "px-3 py-1 text-xs font-semibold rounded-full inline-block leading-tight transition-colors duration-150";
    switch (phase) {
        case ODYSSEY_PHASES.PLANNING:
            return `${base} bg-purple-200 text-purple-800 border border-purple-300`;
        case ODYSSEY_PHASES.AWAITING_PLAN_REVIEW:
        case ODYSSEY_PHASES.AWAITING_MILESTONE_REVIEW:
            return `${base} bg-blue-200 text-blue-800 border border-blue-300`;
        case ODYSSEY_PHASES.EXECUTING_MILESTONE:
            return `${base} bg-green-200 text-green-800 border border-green-300 animate-pulse`;
        case ODYSSEY_PHASES.FINALIZING:
            return `${base} bg-slate-200 text-slate-800 border border-slate-300`;
        case ODYSSEY_PHASES.COMPLETED:
            return `${base} bg-gray-300 text-gray-900 border border-gray-400`;
        default:
            return `${base} bg-gray-100 text-gray-600 border border-gray-200`; // Fallback for unknown phases
    }
};

const OdysseyPhaseBadge = ({ phase }) => {
    if (!phase) {
        return null; // Don't render if phase is not provided
    }

    // Replace underscores with spaces and capitalize for display
    const displayPhase = phase
        .replace(/_/g, ' ')
        .toLowerCase()
        .split(' ')
        .map(word => word.charAt(0).toUpperCase() + word.slice(1))
        .join(' ');

    return (
        <span className={getOdysseyPhasePillClasses(phase)} title={`Odyssey Phase: ${displayPhase}`}>
            {displayPhase}
        </span>
    );
};

export default OdysseyPhaseBadge;
