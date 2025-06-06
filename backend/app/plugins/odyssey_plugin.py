import json
from loguru import logger
from sqlalchemy.orm import Session
from typing import Dict, Any, List # For type hinting

from app.plugins.base_plugin import FrankiePlugin
from app.db import models, schemas # AgentTask model and TaskStatus enum
from app.services.ollama_service import ollama_service # To interact with LLM

# Define phases for the Odyssey plugin. Can be expanded.
ODYSSEY_PHASE_INITIALIZING = "INITIALIZING" # Task just created, plugin instance new
ODYSSEY_PHASE_PLANNING = "PLANNING"
ODYSSEY_PHASE_AWAITING_PLAN_REVIEW = "AWAITING_PLAN_REVIEW"
ODYSSEY_PHASE_EXECUTING_MILESTONE = "EXECUTING_MILESTONE"
ODYSSEY_PHASE_AWAITING_MILESTONE_REVIEW = "AWAITING_MILESTONE_REVIEW"
ODYSSEY_PHASE_FINALIZING = "FINALIZING"
ODYSSEY_PHASE_AWAITING_FINAL_REVIEW = "AWAITING_FINAL_REVIEW" # Before marking as APPLIED
# APPLIED and ERROR are final TaskStatus from models.TaskStatus

class OdysseyPlugin(FrankiePlugin):
    """
    Frankie Plugin: Odyssey Agent (Autonomous General Purpose)
    Handles complex, open-ended tasks by creating a multi-step plan,
    executing milestones (potentially using tools), and pausing for admin
    review at key checkpoints. This initial implementation focuses on the PLANNING phase.
    """

    @staticmethod
    def get_id() -> str:
        return "odyssey_agent"

    @staticmethod
    def get_name() -> str:
        return "Odyssey Agent (Autonomous)"
    
    @staticmethod
    def get_description() -> str:
        return "Manages complex, open-ended tasks via LLM-driven planning and milestone execution, with admin review checkpoints. Capable of research, content generation, and more."

    def __init__(self, db: Session, task: models.AgentTask):
        super().__init__(db, task)
        self.task_specific_data: Dict[str, Any] = {}
        self._load_task_context_data() # Load or initialize phase and data

        # Placeholder for tools this plugin might use in later phases
        # self.tools = { "internet_search": InternetSearchTool(), ... }
        logger.info(f"OdysseyPlugin initialized for task {self.task.id}. Current internal phase: {self.task_specific_data.get('current_phase')}")

    def _load_task_context_data(self):
        """Load ongoing task data from AgentTask.task_context_data (JSON string field)."""
        if self.task.task_context_data:
            try:
                loaded_data = json.loads(self.task.task_context_data)
                if isinstance(loaded_data, dict):
                    self.task_specific_data = loaded_data
                else: # Should be a dict, if not, indicates corruption or old format
                    logger.warning(f"task_context_data for task {self.task.id} is not a dict. Initializing fresh context.")
                    self.task_specific_data = {}
            except json.JSONDecodeError:
                logger.error(f"Failed to decode task_context_data for Odyssey task {self.task.id}. Initializing fresh context.")
                self.task_specific_data = {}
        
        # Ensure 'current_phase' is present, default to PLANNING if new or context was invalid
        if "current_phase" not in self.task_specific_data:
            self.task_specific_data["current_phase"] = ODYSSEY_PHASE_PLANNING
        
        logger.info(f"Odyssey Task {self.task.id} context loaded with phase: {self.task_specific_data['current_phase']}")

    def _get_serialized_task_context_data(self) -> str:
        """Serializes the internal task_specific_data to a JSON string for DB update."""
        return json.dumps(self.task_specific_data)

    async def _phase_planning(self) -> Dict[str, Any]:
        """
        First phase: Takes the user's high-level goal and uses an LLM to generate
        a multi-step plan with milestones, sub-steps, and potential tools.
        """
        logger.info(f"Task {self.task.id} [OdysseyPlugin]: Entering PLANNING sub-phase.")
        user_goal = self.task.prompt

        # Meta-prompt for the LLM to create a plan
        planning_meta_prompt = f"""
        You are "Odyssey Planner," an advanced AI project planning assistant for the Frankie Agent.
        Your task is to take a high-level user goal and break it down into a sequence of actionable milestones and logical sub-steps.
        The user's goal is: "{user_goal}"

        Consider these general capabilities (tools) the agent might use in later phases:
        - InternetSearch: For general research, finding information, APIs, documentation.
        - WebScraper: For extracting specific data from web pages (URLs might be found via InternetSearch).
        - FileSystem: For creating/writing files (e.g., reports, code drafts) in a sandboxed workspace.
        - CodeGenerator: For generating code snippets or full files in various languages.
        - FrankieCodebaseReader: For understanding Frankie's internal structure if the goal is to create a new Frankie plugin.
        - LLMInternal: For reasoning, summarization, data analysis, or generating text content.

        Based on the user's goal, provide a comprehensive project plan. Your response MUST be a single, valid JSON object with the following keys:
        - "project_title": A concise title for this project/task, derived from the user's goal.
        - "overall_summary": A brief (1-3 sentences) summary of your understanding of the goal and your general strategic approach.
        - "clarifying_questions": An array of strings. List any critical questions you (the planner) have for the administrator to clarify the goal BEFORE detailed execution planning of milestones begins. If none, provide an empty array.
        - "milestones": An array of objects. Each milestone object MUST have:
            - "milestone_id": A unique short ID (e.g., "M1", "M2", "M2.1").
            - "name": A concise, descriptive name for the milestone.
            - "description": A detailed (1-3 sentences) description of what this milestone aims to achieve and its primary deliverable or outcome.
            - "estimated_sub_steps": An array of strings, outlining the key logical sub-steps or actions the agent will perform within this milestone.
            - "potential_tools": An array of strings listing the primary types of tools anticipated for this milestone (from the capabilities list above).

        Example for "Research impact of X on Y":
        {{
            "project_title": "Research Report: Impact of X on Y",
            "overall_summary": "This project will research and synthesize information on how X affects Y, culminating in a structured report.",
            "clarifying_questions": ["Is there a specific format or length requirement for the final report?", "Are there any known sources that should be prioritized or avoided?"],
            "milestones": [
                {{
                    "milestone_id": "M1",
                    "name": "Initial Information Gathering & Keyword Definition",
                    "description": "Identify key concepts and search terms, and perform broad internet searches to gather a pool of relevant sources.",
                    "estimated_sub_steps": ["Analyze prompt for core entities and relationships", "Generate list of 5-10 primary search queries", "Execute searches using InternetSearchTool", "Collect top 20-30 URLs for initial review"],
                    "potential_tools": ["LLMInternal", "InternetSearchTool"]
                }},
                {{
                    "milestone_id": "M2",
                    "name": "Source Filtering & Deep Dive",
                    "description": "Filter collected sources for relevance and credibility. Extract detailed information from the most promising sources.",
                    "estimated_sub_steps": ["Categorize URLs by apparent source type (academic, news, blog)", "Prioritize official reports and academic papers", "Use WebScraperTool to extract full text from top 5-7 sources", "Use LLMInternal to summarize each source"],
                    "potential_tools": ["WebScraperTool", "LLMInternal"]
                }},
                // ... more milestones like Drafting, Synthesizing, Formatting Report ...
            ]
        }}
        
        Ensure the plan is logical, breaks the problem down effectively, and sets clear expectations. The first milestone should often focus on deeper understanding or initial information gathering if the prompt is broad.
        """
        
        logger.info(f"Task {self.task.id} [OdysseyPlugin]: Sending planning prompt to LLM.")
        llm_response = await ollama_service.generate_json(planning_meta_prompt)

        if "error" in llm_response or not isinstance(llm_response.get("milestones"), list) or not llm_response.get("project_title"):
            error_msg = f"LLM error during planning phase or malformed plan received: {llm_response.get('error', 'Malformed plan structure from LLM - missing key fields like milestones or project_title.')}"
            logger.error(f"Task {self.task.id} [OdysseyPlugin]: {error_msg}")
            # No change to self.task_specific_data["current_phase"] here, let error status take precedence
            return {
                "status": models.TaskStatus.ERROR, 
                "error_message": error_msg
                # task_context_data will not be updated with a partial/bad plan
            }

        # Store the generated plan and update phase for admin review
        self.task_specific_data["plan"] = llm_response 
        self.task_specific_data["current_milestone_index"] = -1 # Indicates the plan itself is the current item for review
        self.task_specific_data["current_phase"] = ODYSSEY_PHASE_AWAITING_PLAN_REVIEW
        
        # Format a summary of the plan for admin review to be stored in AgentTask.llm_explanation
        plan_summary_for_admin = (
            f"## Proposed Project Plan: {llm_response.get('project_title', self.task.prompt[:50] + '...')}\n\n"
            f"**Agent's Understanding & Approach:**\n{llm_response.get('overall_summary', 'Details are in the full plan structure below.')}\n\n"
        )
        if llm_response.get('clarifying_questions'):
            plan_summary_for_admin += "**Clarifying Questions for You (Admin):**\n"
            for i, q_text in enumerate(llm_response['clarifying_questions']):
                plan_summary_for_admin += f"  {i+1}. {q_text}\n"
            plan_summary_for_admin += "\n"
        else:
            plan_summary_for_admin += "**No immediate clarifying questions from the agent.**\n\n"
        
        plan_summary_for_admin += "**Proposed Milestones:**\n"
        if llm_response.get('milestones'):
            for i, milestone in enumerate(llm_response['milestones']):
                plan_summary_for_admin += (
                    f"  {i+1}. **{milestone.get('name', 'Unnamed Milestone')}** (ID: {milestone.get('milestone_id', f'M{i+1}')})\n"
                    f"     *Description:* {milestone.get('description', 'N/A')}\n"
                    f"     *Key Sub-steps:* {'; '.join(milestone.get('estimated_sub_steps', ['N/A']))}\n"
                    f"     *Potential Tools:* {', '.join(milestone.get('potential_tools', ['N/A']))}\n\n"
                )
        else:
            plan_summary_for_admin += "No milestones were defined by the LLM. The plan might be incomplete or the task very simple.\n\n"
            
        plan_summary_for_admin += "Please review this plan. If you approve, the agent will proceed with the first milestone. You can also provide feedback or reject the plan."
        
        logger.info(f"Task {self.task.id} [OdysseyPlugin]: Plan generated successfully, status set to AWAITING_REVIEW for plan approval.")
        return {
            "status": models.TaskStatus.AWAITING_REVIEW, # Generic status, context implies plan review
            "llm_explanation": plan_summary_for_admin.strip(), # This will be shown in the review UI
            "proposed_diff": "", # No code diff at the planning stage
            "test_status": models.TestStatus.NOT_RUN, # No tests at planning stage
            "task_context_data": self._get_serialized_task_context_data() # Store the full plan & new phase
        }

    # Placeholder for future milestone execution logic
    async def _phase_execute_milestone(self) -> Dict[str, Any]:
        logger.info(f"Task {self.task.id} [OdysseyPlugin]: Placeholder for _phase_execute_milestone.")
        # This method will be implemented in a subsequent step.
        # It will retrieve the current milestone from self.task_specific_data["plan"]
        # using self.task_specific_data["current_milestone_index"],
        # then execute its sub-steps using tools and LLM calls.
        # Upon completion, it will update self.task_specific_data["current_phase"] to
        # ODYSSEY_PHASE_AWAITING_MILESTONE_REVIEW and return results.
        return {
            "status": models.TaskStatus.ERROR,
            "error_message": "Milestone execution phase not yet implemented.",
            "task_context_data": self._get_serialized_task_context_data()
        }
        
    async def _phase_finalizing(self) -> Dict[str, Any]:
        logger.info(f"Task {self.task.id} [OdysseyPlugin]: Placeholder for _phase_finalizing.")
        return {
            "status": models.TaskStatus.APPLIED, # Or AWAITING_FINAL_REVIEW
            "llm_explanation": "All milestones completed. Task finalized (placeholder).",
            "task_context_data": self._get_serialized_task_context_data()
        }


    async def execute(self) -> Dict[str, Any]:
        """
        Main execution entry point for the Odyssey Plugin.
        Acts as a state machine based on `self.task_specific_data['current_phase']`.
        Admin approvals via API will trigger phase transitions before this method is called again.
        """
        current_phase = self.task_specific_data.get("current_phase", ODYSSEY_PHASE_PLANNING)
        logger.info(f"Task {self.task.id} [OdysseyPlugin]: Execute called. Internal phase: '{current_phase}'")

        if current_phase == ODYSSEY_PHASE_PLANNING:
            return await self._phase_planning()
        
        # The transitions to EXECUTING_MILESTONE or FINALIZING will be handled by the
        # admin approval endpoint, which will update `task_context_data` (including `current_phase`
        # and `current_milestone_index`) and then re-queue the task.
        # The orchestrator will then call this `execute` method again.
        
        elif current_phase == ODYSSEY_PHASE_EXECUTING_MILESTONE:
            # This phase means an admin has approved the plan or a previous milestone,
            # and the orchestrator (via an API endpoint) has set this phase and the
            # correct current_milestone_index in task_context_data.
            return await self._phase_execute_milestone()
            
        elif current_phase == ODYSSEY_PHASE_FINALIZING:
            return await self._phase_finalizing()
            
        elif current_phase in [ODYSSEY_PHASE_AWAITING_PLAN_REVIEW, ODYSSEY_PHASE_AWAITING_MILESTONE_REVIEW, ODYSSEY_PHASE_AWAITING_FINAL_REVIEW]:
            # If orchestrator calls execute while it's already awaiting review,
            # it means no admin action has happened yet to change the phase.
            # The plugin should simply re-assert its current state.
            logger.info(f"Task {self.task.id} [OdysseyPlugin]: In phase '{current_phase}', awaiting admin action. No execution needed by plugin.")
            return { # Return current state without re-processing
                "status": models.TaskStatus.AWAITING_REVIEW, # Keep it in review
                "llm_explanation": self.task.llm_explanation, # Existing explanation
                "proposed_diff": self.task.proposed_diff,
                "test_status": self.task.test_status,
                "task_context_data": self.task.task_context_data # Current context
            }
        
        # Default or unexpected phase, perhaps re-evaluate or error
        logger.warning(f"Task {self.task.id} [OdysseyPlugin]: Reached execute with unhandled or unexpected internal phase '{current_phase}'. Defaulting to re-initiate planning.")
        self.task_specific_data["current_phase"] = ODYSSEY_PHASE_PLANNING # Fallback
        return await self._phase_planning()