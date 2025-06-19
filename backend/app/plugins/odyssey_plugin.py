import json
from loguru import logger
from sqlalchemy.orm import Session
from typing import Dict, Any

from app.plugins.base_plugin import FrankiePlugin
from app.db import models # For models and enums like TaskStatus
from app.services.ollama_service import ollama_service

# Define phases for the Odyssey plugin's internal state machine
_PHASE_PLANNING = "PLANNING"
_PHASE_AWAITING_PLAN_REVIEW = "AWAITING_PLAN_REVIEW"
_PHASE_EXECUTING_MILESTONE = "EXECUTING_MILESTONE"
_PHASE_AWAITING_MILESTONE_REVIEW = "AWAITING_MILESTONE_REVIEW"
_PHASE_FINALIZING = "FINALIZING"
_PHASE_COMPLETED = "COMPLETED"

class OdysseyPlugin(FrankiePlugin):
    """
    Frankie Plugin: Odyssey Agent (Autonomous General Purpose)
    Handles complex, open-ended tasks by creating a multi-step plan,
    executing milestones, and pausing for admin review at key checkpoints.
    """

    @staticmethod
    def get_id() -> str:
        return "odyssey_agent"

    @staticmethod
    def get_name() -> str:
        return "Odyssey Agent (Autonomous)"
    
    @staticmethod
    def get_description() -> str:
        return "Handles complex, open-ended tasks via LLM-driven planning and milestone execution with admin review."

    def __init__(self, db: Session, task: models.AgentTask):
        super().__init__(db, task)
        self.task_specific_data: Dict[str, Any] = {}
        self._load_task_context_data()

    def _load_task_context_data(self):
        """Load and initialize ongoing task data from the AgentTask's JSON context field."""
        if self.task.task_context_data:
            try:
                self.task_specific_data = json.loads(self.task.task_context_data)
                if "current_phase" not in self.task_specific_data:
                    self.task_specific_data["current_phase"] = _PHASE_PLANNING
            except json.JSONDecodeError:
                self.task_specific_data = {"current_phase": _PHASE_PLANNING}
        else:
            self.task_specific_data = {"current_phase": _PHASE_PLANNING}
        logger.info(f"OdysseyPlugin Task {self.task.id} loaded with internal phase: {self.task_specific_data['current_phase']}")

    def _get_serialized_task_context_data(self) -> str:
        """Serializes the internal task data to a JSON string for database storage."""
        return json.dumps(self.task_specific_data)

    async def _phase_planning(self) -> Dict[str, Any]:
        """
        The first phase: Takes the user's high-level goal and uses an LLM to generate a plan.
        """
        logger.info(f"Task {self.task.id} [OdysseyPlugin]: Entering PLANNING phase.")
        user_goal = self.task.prompt

        planning_meta_prompt = f"""
        You are "Odyssey Planner," an advanced AI project planning assistant for the Frankie Agent.
        Your task is to take a high-level user goal and break it down into a sequence of actionable milestones and logical sub-steps.
        The user's goal is: "{user_goal}"

        Consider these general capabilities (tools) the agent might use in later phases:
        - InternetSearch: For general web research.
        - WebScraper: For extracting specific data from web pages.
        - FileSystem: For creating/writing files (e.g., reports, code drafts) in a sandboxed workspace.
        - CodeGenerator: For generating code snippets or full files.
        - FrankieCodebaseReader: For understanding Frankie's internal structure if the goal is to create a new Frankie plugin.
        - LLMInternal: For reasoning, summarization, or text generation.

        Based on the user's goal, provide a comprehensive project plan. Your response MUST be a single, valid JSON object with the following keys:
        - "project_title": A concise title for this project.
        - "overall_summary": A brief summary of your understanding of the goal and your approach.
        - "clarifying_questions": An array of strings listing any critical questions for the administrator. If none, provide an empty array.
        - "milestones": An array of objects. Each milestone object must have "milestone_id" (e.g., "M1"), "name", "description", "estimated_sub_steps" (an array of strings), and "potential_tools" (an array of strings).
        """
        
        llm_response = await ollama_service.generate_json(planning_meta_prompt)

        if "error" in llm_response or not isinstance(llm_response.get("milestones"), list):
            error_msg = f"LLM error during planning phase or malformed plan received: {llm_response.get('error', 'Malformed plan structure.')}"
            return {"status": models.TaskStatus.ERROR, "error_message": error_msg}

        self.task_specific_data["plan"] = llm_response
        self.task_specific_data["current_milestone_index"] = -1
        self.task_specific_data["current_phase"] = _PHASE_AWAITING_PLAN_REVIEW
        
        plan_summary_for_admin = f"## Proposed Plan: {llm_response.get('project_title', 'New Project')}\n\n**Summary:**\n{llm_response.get('overall_summary', 'N/A')}\n\n"
        if llm_response.get('clarifying_questions'):
            plan_summary_for_admin += "**Clarifying Questions:**\n" + "\n".join([f"- {q}" for q in llm_response['clarifying_questions']]) + "\n\n"
        plan_summary_for_admin += "**Milestones:**\n"
        for i, milestone in enumerate(llm_response.get('milestones', [])):
            plan_summary_for_admin += f"  {i+1}. **{milestone.get('name', 'N/A')}**\n     *Desc:* {milestone.get('description', 'N/A')}\n\n"
        plan_summary_for_admin += "Please review this plan. If you approve, I will begin with the first milestone."
        
        logger.info(f"Task {self.task.id} [OdysseyPlugin]: Plan generated, ready for admin review.")
        return {
            "status": models.TaskStatus.AWAITING_REVIEW,
            "llm_explanation": plan_summary_for_admin,
            "task_context_data": self._get_serialized_task_context_data()
        }

    async def _phase_execute_milestone(self) -> Dict[str, Any]:
        """
        Executes the current milestone based on the plan.
        This phase is triggered after an admin approves a plan or a previous milestone.
        """
        logger.info(f"Task {self.task.id} [OdysseyPlugin]: Entering EXECUTING_MILESTONE phase.")

        plan = self.task_specific_data.get("plan")
        if not plan or not isinstance(plan.get("milestones"), list) or not plan["milestones"]:
            logger.error(f"Task {self.task.id} [OdysseyPlugin]: Plan or milestones missing or empty in task_specific_data.")
            return {"status": models.TaskStatus.ERROR, "error_message": "Missing or invalid plan for milestone execution."}

        milestones = plan["milestones"]
        current_milestone_index = self.task_specific_data.get("current_milestone_index", -1)
        current_milestone_index += 1
        self.task_specific_data["current_milestone_index"] = current_milestone_index

        if current_milestone_index >= len(milestones):
            logger.error(f"Task {self.task.id} [OdysseyPlugin]: current_milestone_index ({current_milestone_index}) is out of bounds for milestones length ({len(milestones)}). Should have gone to FINALIZING.")
            # This state should ideally not be reached if logic is correct, might go to finalizing.
            self.task_specific_data["current_phase"] = _PHASE_FINALIZING
            return {
                "status": models.TaskStatus.IN_PROGRESS,
                "llm_explanation": "All milestones executed. Proceeding to finalization.",
                "task_context_data": self._get_serialized_task_context_data()
            }

        current_milestone = milestones[current_milestone_index]
        milestone_name = current_milestone.get("name", f"Milestone {current_milestone_index + 1}")
        logger.info(f"Task {self.task.id} [OdysseyPlugin]: Executing milestone: {milestone_name}")

        llm_explanation = f"**Milestone Execution: {milestone_name}**\n\n"
        llm_explanation += f"Description: {current_milestone.get('description', 'N/A')}\n"

        # Simulate tool usage
        potential_tools = current_milestone.get("potential_tools", [])
        if potential_tools:
            selected_tool = potential_tools[0] # Select the first tool
            logger.info(f"Task {self.task.id} [OdysseyPlugin]: Simulating use of tool '{selected_tool}' for milestone '{milestone_name}'.")
            llm_explanation += f"Tool Used (Simulated): {selected_tool}\n"
        else:
            llm_explanation += "No specific tools listed for this milestone; general processing simulated.\n"

        # Determine next phase
        next_phase: str
        next_status: models.TaskStatus

        if current_milestone_index < len(milestones) - 1:
            next_phase = _PHASE_AWAITING_MILESTONE_REVIEW
            next_status = models.TaskStatus.AWAITING_REVIEW
            next_milestone_name = milestones[current_milestone_index + 1].get("name", f"Milestone {current_milestone_index + 2}")
            llm_explanation += f"\nMilestone '{milestone_name}' execution simulated. The results are now ready for your review. Next up: '{next_milestone_name}'."
            logger.info(f"Task {self.task.id} [OdysseyPlugin]: Milestone '{milestone_name}' completed. Awaiting review for next milestone.")
        else:
            next_phase = _PHASE_FINALIZING
            next_status = models.TaskStatus.IN_PROGRESS # Finalizing is an active step
            llm_explanation += f"\nMilestone '{milestone_name}' (final milestone) execution simulated. Proceeding to finalization."
            logger.info(f"Task {self.task.id} [OdysseyPlugin]: Final milestone '{milestone_name}' completed. Moving to FINALIZING phase.")

        self.task_specific_data["current_phase"] = next_phase

        return {
            "status": next_status,
            "llm_explanation": llm_explanation,
            "task_context_data": self._get_serialized_task_context_data()
        }

    async def execute(self) -> Dict[str, Any]:
        """Main entry point. Acts as a state machine for the plugin's lifecycle."""
        current_phase = self.task_specific_data.get("current_phase", _PHASE_PLANNING)
        logger.info(f"Task {self.task.id} [OdysseyPlugin]: Execute called. Internal phase: '{current_phase}'")

        if current_phase == _PHASE_PLANNING:
            self.task.status = models.TaskStatus.PLANNING # Update main status for UI feedback
            return await self._phase_planning()
        
        elif current_phase == _PHASE_EXECUTING_MILESTONE:
            # This phase is entered after an admin approves a plan or a previous milestone.
            self.task.status = models.TaskStatus.IN_PROGRESS # Update main status for UI feedback
            return await self._phase_execute_milestone()
            
        elif current_phase in [_PHASE_AWAITING_PLAN_REVIEW, _PHASE_AWAITING_MILESTONE_REVIEW]:
             logger.info(f"Task {self.task.id} [OdysseyPlugin]: In phase '{current_phase}', awaiting admin action. No plugin execution needed.")
             return {} # Return empty dict; orchestrator will not update the task.

        elif current_phase == _PHASE_FINALIZING:
            logger.info(f"Task {self.task.id} [OdysseyPlugin]: Entering FINALIZING phase.")
            # For now, finalization directly transitions to completed.
            # Future: Could involve report generation, cleanup, etc.
            self.task_specific_data['current_phase'] = _PHASE_COMPLETED
            self.task.status = models.TaskStatus.COMPLETED
            logger.info(f"Task {self.task.id} [OdysseyPlugin]: Task finalized and moved to COMPLETED phase.")
            return {
                "status": models.TaskStatus.COMPLETED,
                "llm_explanation": "Task finalization complete. All milestones processed.",
                "task_context_data": self._get_serialized_task_context_data()
            }

        elif current_phase == _PHASE_COMPLETED:
            logger.info(f"Task {self.task.id} [OdysseyPlugin]: Task is already in COMPLETED phase.")
            return {
                "status": models.TaskStatus.COMPLETED, # Ensure orchestrator knows it's still completed
                "llm_explanation": "This task has already been completed.",
                "task_context_data": self._get_serialized_task_context_data() # Persist current state if anything changed unexpectedly
            }
        
        # Default case for unexpected or unhandled phases
        logger.warning(f"Task {self.task.id} [OdysseyPlugin]: Reached execute with unhandled phase '{current_phase}'.")
        return {"status": models.TaskStatus.ERROR, "error_message": f"Unhandled plugin phase: {current_phase}"}