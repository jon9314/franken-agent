from loguru import logger
from typing import List, Dict, Any # For type hinting
import time

from app.plugins.base_plugin import FrankiePlugin
from app.db import models, crud, schemas # Ensure schemas is imported for ResearchFindingCreate
from app.genealogy_tools.findagrave_tool import FindAGraveTool
# from app.genealogy_tools.familysearch_tool import FamilySearchTool # Example for future
from app.services.ollama_service import ollama_service
from app.core.config import settings # To potentially access API keys for tools

class GenealogyResearchPlugin(FrankiePlugin):
    """
    A plugin for researching missing information in a family tree using various online sources
    and an LLM to synthesize findings.
    """

    @staticmethod
    def get_id() -> str:
        return "genealogy_researcher"

    @staticmethod
    def get_name() -> str:
        return "Genealogy Researcher"
    
    @staticmethod
    def get_description() -> str:
        return "Uses online sources to find missing data for people in a family tree and suggests findings for admin review."

    def __init__(self, db, task):
        super().__init__(db, task)
        self.person_to_research: models.Person | None = None
        
        # Initialize tools - more tools can be added here
        self.tools = []
        self.tools.append(FindAGraveTool()) # No API key needed for this example tool
        
        # Example of adding a tool that might need an API key:
        # if settings.FAMILYSEARCH_DEV_KEY:
        #     self.tools.append(FamilySearchTool(api_key=settings.FAMILYSEARCH_DEV_KEY))
        # else:
        #     logger.info("FamilySearchTool not configured due to missing FAMILYSEARCH_DEV_KEY.")
            
        # Filter out tools that are not configured (e.g., missing API keys)
        self.tools = [tool for tool in self.tools if tool.is_configured]
        logger.info(f"GenealogyResearchPlugin initialized for task {self.task.id} with {len(self.tools)} configured tools: {[t.name for t in self.tools]}")

    def _identify_missing_info_fields(self) -> List[str]:
        """Identifies key pieces of information that are missing for the target person."""
        if not self.person_to_research:
            logger.warning(f"Cannot identify missing info: person_to_research not set for task {self.task.id}")
            return []
        
        missing_fields = []
        p = self.person_to_research
        if not p.birth_date: missing_fields.append("birth_date")
        if not p.birth_place: missing_fields.append("birth_place")
        if not p.death_date: missing_fields.append("death_date")
        if not p.death_place: missing_fields.append("death_place")
        
        # Example: Check for parents. A person has parents if they are listed as a child in any family.
        # This requires querying the database.
        families_where_person_is_child = self.db.query(models.Family).filter(models.Family.children.any(id=p.id)).count()
        if families_where_person_is_child == 0:
            missing_fields.append("parents") # This could be further broken down by LLM into 'father_name', 'mother_name'
            
        logger.info(f"For person ID {p.id} ({p.first_name} {p.last_name}), identified missing info fields: {missing_fields}")
        return missing_fields

    async def _synthesize_findings_with_llm(self, person: models.Person, raw_findings: List[Dict[str, Any]], field_being_researched: str):
        """
        Uses an LLM to analyze raw findings for a specific field, score them,
        generate reasoning, a citation, and create a ResearchFinding record if confident.
        """
        if not raw_findings:
            logger.info(f"No raw findings to synthesize for '{field_being_researched}' of person ID {person.id}.")
            return

        # Prepare known data for context to the LLM
        known_data_str = f"""
        - Full Name: {person.first_name or 'N/A'} {person.last_name or 'N/A'} (GEDCOM ID: {person.gedcom_id})
        - Sex: {person.sex or 'N/A'}
        - Birth Date: {person.birth_date or 'Unknown'}
        - Birth Place: {person.birth_place or 'Unknown'}
        - Death Date: {person.death_date or 'Unknown'}
        - Death Place: {person.death_place or 'Unknown'}
        """

        # Prepare raw findings for the prompt, making it readable
        raw_findings_formatted_list = []
        for i, f_dict in enumerate(raw_findings):
            raw_findings_formatted_list.append(
                f"  Finding {i+1} (Source: {f_dict.get('source_name', 'Unknown')}):\n"
                f"    - Data Field Found: {f_dict.get('data_field', 'N/A')}\n"
                f"    - Value Found: {f_dict.get('value', 'N/A')}\n"
                f"    - URL: {f_dict.get('source_url', 'N/A')}\n"
                f"    - Citation/Notes: {f_dict.get('citation', f_dict.get('match_quality_notes', 'N/A'))}"
            )
        raw_findings_str = "\n".join(raw_findings_formatted_list)

        prompt = f"""
        You are an expert genealogist and data analyst. Your task is to analyze a set of raw research findings for a specific individual and a specific data field they are missing or need to verify.

        Individual's Known Information:
        {known_data_str}

        Specific Data Field Currently Being Researched: '{field_being_researched}'

        Raw Research Findings (potentially related to '{field_being_researched}' or the individual in general):
        {raw_findings_str}

        Instructions:
        1.  Carefully review all findings. Consider consistency, source reliability (e.g., a direct vital record image is better than an unsourced tree entry), and how well they match the known data for the individual.
        2.  Determine the most probable value ONLY for the specific '{field_being_researched}'.
        3.  Provide a confidence score (integer from 0 to 100) for your suggested value FOR THIS SPECIFIC FIELD. A score of 0 means no confident suggestion can be made for this field from these findings.
        4.  Provide a brief reasoning (1-3 sentences) explaining your confidence and choice for this specific field, especially if there are conflicting findings or if you are inferring from related data.
        5.  Formulate a concise source citation string based on the provided source names and URLs that DIRECTLY support your suggestion for this field. If multiple sources support the same fact, list the primary ones.

        Respond ONLY with a single, valid JSON object with the following keys:
        - "suggested_value": The most probable value for '{field_being_researched}' (string, formatted appropriately for the data type, e.g., dates as "DD MMM YYYY", places as "City, County, State, Country"). If suggesting a name for a parent, provide the full name.
        - "confidence_score": Your confidence in this suggestion (integer, 0-100).
        - "llm_reasoning": Your brief reasoning for this specific suggestion (string).
        - "citation_text": A concise citation for the supporting source(s) for this specific suggestion (string).

        If no confident suggestion can be made for '{field_being_researched}' based on the provided findings, ensure "confidence_score" is low (e.g., below 30) or 0.
        """
        
        logger.info(f"Sending synthesis prompt to LLM for person ID {person.id}, field '{field_being_researched}' with {len(raw_findings)} raw findings.")
        response_json = await ollama_service.generate_json(prompt)
        
        if response_json and "error" not in response_json and response_json.get("confidence_score", 0) >= 30: # Confidence threshold for saving a finding
            original_value = getattr(person, field_being_researched, None) # Get current value if field exists
            
            # Data for creating ResearchFinding record
            finding_create_data = schemas.ResearchFindingCreate(
                person_id=person.id,
                agent_task_id=self.task.id, # Link finding to the agent task
                data_field=field_being_researched, # The field this finding is about
                original_value=str(original_value) if original_value is not None else None,
                suggested_value=response_json.get("suggested_value"),
                confidence_score=response_json.get("confidence_score"),
                llm_reasoning=response_json.get("llm_reasoning"),
                # Consolidate source names from the raw findings that contributed
                source_name=", ".join(set(f.get('source_name', 'Unknown Source') for f in raw_findings if f.get('source_name'))),
                # Try to get a relevant URL, could be more sophisticated
                source_url=next((f.get('source_url') for f in raw_findings if f.get('source_url')), None),
                citation_text=response_json.get("citation_text", "Citation not generated by LLM."),
            )
            crud.create_research_finding(self.db, finding_in=finding_create_data)
            logger.info(f"Created ResearchFinding for person ID {person.id}, field '{field_being_researched}' with confidence {finding_create_data.confidence_score}")
        else:
            error_info = response_json.get('error', 'Low confidence or no suggestion from LLM') if response_json else 'No valid JSON response from LLM for synthesis'
            logger.info(f"LLM synthesis for '{field_being_researched}' (person ID {person.id}) did not yield a confident result or had an error: {error_info}")


    async def execute(self) -> Dict[str, Any]:
        """Main execution logic for the GenealogyResearchPlugin."""
        start_time = time.time()
        logger.info(f"[{self.get_name()}] Starting research for task #{self.task.id} on person_id: {self.task.target_person_id}")
        
        if not self.task.target_person_id:
            return {"status": models.TaskStatus.ERROR, "error_message": "No target person ID specified for genealogy research."}
            
        self.person_to_research = crud.get_person_by_id(self.db, person_id=self.task.target_person_id)
        if not self.person_to_research:
            return {"status": models.TaskStatus.ERROR, "error_message": f"Target person with ID {self.task.target_person_id} not found in database."}

        missing_info_fields = self._identify_missing_info_fields()
        if not missing_info_fields:
            logger.info(f"No missing information identified for person {self.person_to_research.id} to research.")
            return {"status": models.TaskStatus.APPLIED, "llm_explanation": "No missing information identified for this person to research. Task considered complete as no action was needed."}
        
        logger.info(f"Will research missing fields: {missing_info_fields} for person ID {self.person_to_research.id} ({self.person_to_research.first_name} {self.person_to_research.last_name})")

        total_raw_findings_collected = 0
        for field_to_research_currently in missing_info_fields:
            all_raw_findings_for_this_field: List[Dict[str, Any]] = []
            logger.info(f"--- Researching field: '{field_to_research_currently}' for person {self.person_to_research.id} ---")
            
            for tool_instance in self.tools:
                logger.info(f"Using tool '{tool_instance.name}' to research '{field_to_research_currently}' for person {self.person_to_research.id}")
                try:
                    # The search_person method of the tool should ideally try to find info related to the person.
                    # The LLM will then be asked to synthesize based on the field_to_research_currently.
                    tool_raw_results: List[Dict[str, Any]] = await tool_instance.search_person(self.person_to_research)
                    
                    for finding_dict in tool_raw_results:
                        finding_dict['source_name'] = tool_instance.name # Ensure source name is attached
                        all_raw_findings_for_this_field.append(finding_dict)
                    
                    logger.info(f"Tool '{tool_instance.name}' returned {len(tool_raw_results)} raw items potentially related to person {self.person_to_research.id}.")
                    total_raw_findings_collected += len(tool_raw_results)
                except Exception as e:
                    logger.error(f"Error using tool '{tool_instance.name}' for person {self.person_to_research.id}: {e}", exc_info=True)

            if all_raw_findings_for_this_field:
                logger.info(f"Synthesizing {len(all_raw_findings_for_this_field)} raw findings for field '{field_to_research_currently}' for person {self.person_to_research.id}.")
                await self._synthesize_findings_with_llm(self.person_to_research, all_raw_findings_for_this_field, field_to_research_currently)
            else:
                logger.info(f"No raw findings gathered from any tool for field '{field_to_research_currently}' for person {self.person_to_research.id}.")
        
        # After iterating through all missing fields, count how many actual ResearchFinding records were created and are unverified
        newly_created_unverified_findings = self.db.query(models.ResearchFinding).filter(
            models.ResearchFinding.agent_task_id == self.task.id, # Filter by current task
            models.ResearchFinding.status == models.FindingStatus.UNVERIFIED
        ).count()
        
        end_time = time.time()
        duration = end_time - start_time
        logger.info(f"Genealogy research for task #{self.task.id} completed in {duration:.2f} seconds. {newly_created_unverified_findings} new findings created and awaiting review.")

        # The task status is 'APPLIED' from the orchestrator's perspective meaning the plugin ran.
        # The 'AWAITING_REVIEW' is for the findings themselves.
        if newly_created_unverified_findings > 0 :
             return {"status": models.TaskStatus.APPLIED, "llm_explanation": f"Research process complete. {newly_created_unverified_findings} potential new findings were identified and have been saved for your review in the Genealogy Review panel."}
        else:
             return {"status": models.TaskStatus.APPLIED, "llm_explanation": "Research process complete. No new confident suggestions were found for the missing information based on available sources and tools."}
