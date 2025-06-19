import json
import random
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
            logger.error(f"Task {self.task.id} [OdysseyPlugin]: Missing or invalid plan for milestone execution. Plan: {plan}")
            return {
                "status": models.TaskStatus.ERROR,
                "error_message": "Missing or invalid plan for milestone execution.",
                "task_context_data": self._get_serialized_task_context_data()
            }

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
        logger.info(f"Task {self.task.id} [OdysseyPlugin]: Simulating execution of milestone: {milestone_name}")

        llm_explanation = f"**Simulated Milestone Execution: {milestone_name}**\n\n"
        llm_explanation += f"Description: {current_milestone.get('description', 'N/A')}\n"

        # Simulate tool usage
        potential_tools = current_milestone.get("potential_tools", [])
        if potential_tools:
            selected_tool = random.choice(potential_tools) # Randomly select a tool
            logger.info(f"Task {self.task.id} [OdysseyPlugin]: Randomly selected tool '{selected_tool}' for simulated use in milestone '{milestone_name}'.")
            llm_explanation += f"Simulated Using Tool: {selected_tool}\n"
        else:
            llm_explanation += "No specific tools listed for this milestone; general processing simulated without a specific tool.\n"

        # Determine next phase
        next_phase: str
        next_status: models.TaskStatus

        if current_milestone_index < len(milestones) - 1:
            next_phase = _PHASE_AWAITING_MILESTONE_REVIEW
            next_status = models.TaskStatus.AWAITING_REVIEW
            next_milestone_name = milestones[current_milestone_index + 1].get("name", f"Milestone {current_milestone_index + 2}")
            llm_explanation += f"\nSimulated execution of milestone '{milestone_name}' is complete. The results are now ready for your review. Next up: '{next_milestone_name}'."
            logger.info(f"Task {self.task.id} [OdysseyPlugin]: Simulated milestone '{milestone_name}' completed. Awaiting review for next milestone.")
        else:
            next_phase = _PHASE_FINALIZING
            next_status = models.TaskStatus.IN_PROGRESS # Finalizing is an active step
            llm_explanation += f"\nSimulated execution of milestone '{milestone_name}' (final milestone) is complete. Proceeding to finalization."
            logger.info(f"Task {self.task.id} [OdysseyPlugin]: Final simulated milestone '{milestone_name}' completed. Moving to FINALIZING phase.")

        self.task_specific_data["current_phase"] = next_phase

        return {
            "status": next_status,
            "llm_explanation": llm_explanation,
            "task_context_data": self._get_serialized_task_context_data()
        }

    async def _phase_awaiting_milestone_review(self) -> Dict[str, Any]:
        """
        Processes an admin's response to a completed milestone.
        This method is called when the task is in AWAITING_MILESTONE_REVIEW phase and execute() is triggered.
        """
        logger.info(f"Task {self.task.id} [OdysseyPlugin]: Processing admin response in AWAITING_MILESTONE_REVIEW phase.")

        admin_response_raw = self.task.admin_response
        if admin_response_raw is None:
            logger.info(f"Task {self.task.id} [OdysseyPlugin]: No admin response found. Returning empty to wait.")
            return {} # No response yet, orchestrator should not update, plugin waits.

        logger.info(f"Task {self.task.id} [OdysseyPlugin]: Processing admin_response: '{admin_response_raw}'")
        admin_response = admin_response_raw.lower().strip()

        # Clear the admin response once processed
        self.task.admin_response = None # TODO: Ensure this is persisted by the orchestrator if the dict is returned.
                                        # This might need to be part of the returned dict to be saved by orchestrator.
                                        # For now, assuming direct modification is picked up or handled by orchestrator saving task.

        next_phase = None # Using None to indicate if a phase change decision was made
        status: models.TaskStatus = models.TaskStatus.AWAITING_REVIEW # Default to no change
        llm_explanation = ""

        plan = self.task_specific_data.get("plan", {})
        milestones = plan.get("milestones", [])
        num_milestones = len(milestones)
        current_idx = self.task_specific_data.get("current_milestone_index", -1)

        if admin_response in ["approve", "continue"]:
            logger.info(f"Task {self.task.id} [OdysseyPlugin]: Admin approved milestone {current_idx + 1}.")
            if current_idx < num_milestones - 1:
                next_phase = _PHASE_EXECUTING_MILESTONE
                status = models.TaskStatus.IN_PROGRESS
                next_milestone_name = milestones[current_idx + 1]['name'] if (current_idx + 1) < num_milestones else "Next"
                llm_explanation = f"Admin approved. Proceeding to execute next milestone: '{next_milestone_name}'."
            else:
                next_phase = _PHASE_FINALIZING
                status = models.TaskStatus.IN_PROGRESS
                llm_explanation = "Admin approved. All milestones complete. Proceeding to finalization."

        elif admin_response == "skip":
            logger.info(f"Task {self.task.id} [OdysseyPlugin]: Admin chose to skip milestone {current_idx + 1}.")
            skipped_milestone_name = milestones[current_idx]['name'] if 0 <= current_idx < num_milestones else "previous milestone"

            new_idx = current_idx + 1
            self.task_specific_data['current_milestone_index'] = new_idx # Update index to reflect skip

            if new_idx < num_milestones: # If there's a valid next milestone to execute
                next_phase = _PHASE_EXECUTING_MILESTONE
                status = models.TaskStatus.IN_PROGRESS
                next_milestone_name = milestones[new_idx]['name']
                llm_explanation = f"Admin skipped milestone '{skipped_milestone_name}'. Proceeding to execute milestone '{next_milestone_name}'."
            else: # Skipped the last milestone, or skipped into finalization
                next_phase = _PHASE_FINALIZING
                status = models.TaskStatus.IN_PROGRESS
                llm_explanation = f"Admin skipped milestone '{skipped_milestone_name}'. No more milestones to execute directly. Proceeding to finalization."

        elif admin_response in ["stop", "cancel"]:
            logger.info(f"Task {self.task.id} [OdysseyPlugin]: Admin cancelled the task.")
            next_phase = _PHASE_COMPLETED
            status = models.TaskStatus.CANCELLED
            llm_explanation = "Admin cancelled the task at milestone review."

        elif admin_response in ["replan", "modify"]:
            logger.info(f"Task {self.task.id} [OdysseyPlugin]: Admin requested replanning.")
            next_phase = _PHASE_PLANNING
            status = models.TaskStatus.PLANNING
            llm_explanation = "Admin requested replanning. Returning to planning phase."

        else:
            logger.warning(f"Task {self.task.id} [OdysseyPlugin]: Unknown admin response: '{admin_response_raw}'.")
            # status remains AWAITING_REVIEW
            llm_explanation = f"Unknown admin response: '{admin_response_raw}'. Please provide a valid input (e.g., approve, skip, stop, replan)."
            # next_phase remains None, so current_phase in task_specific_data is not updated.

        if next_phase is not None:
            self.task_specific_data['current_phase'] = next_phase

        return {
            "status": status,
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

        elif current_phase == _PHASE_AWAITING_PLAN_REVIEW:
            self.task.status = models.TaskStatus.AWAITING_REVIEW # Ensure status is set
            logger.info(f"Task {self.task.id} [OdysseyPlugin]: In phase '{current_phase}', awaiting admin action for plan. No active plugin execution.")
            return {} # Orchestrator handles this state; plugin has no action until approval/rejection

        elif current_phase == _PHASE_AWAITING_MILESTONE_REVIEW:
            logger.info(f"Task {self.task.id} [OdysseyPlugin]: Execute called during AWAITING_MILESTONE_REVIEW. Checking for admin response.")
            phase_result = await self._phase_awaiting_milestone_review()

            if phase_result: # If dictionary is not empty, an admin response was processed
                self.task.status = phase_result.get("status", models.TaskStatus.AWAITING_REVIEW) # Update task status from phase_result
                # The phase_result already contains llm_explanation and task_context_data
                return phase_result
            else:
                # No admin response processed, task remains in awaiting review.
                # Ensure task status reflects this if it was changed by a previous run.
                self.task.status = models.TaskStatus.AWAITING_REVIEW
                return {} # Return empty, orchestrator doesn't update task.
        
        elif current_phase == _PHASE_EXECUTING_MILESTONE:
            # This phase is entered after an admin approves a plan or a previous milestone.
            self.task.status = models.TaskStatus.IN_PROGRESS # Update main status for UI feedback
            return await self._phase_execute_milestone()
            
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