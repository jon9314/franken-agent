from abc import ABC, abstractmethod
from sqlalchemy.orm import Session
from app.db.models import AgentTask # Ensure AgentTask is imported for type hinting

class FrankiePlugin(ABC):
    """
    Abstract Base Class for all Frankie plugins.
    Each plugin represents a distinct capability or task that the agent can perform.
    """

    def __init__(self, db: Session, task: AgentTask):
        """
        Initializes the plugin instance.

        Args:
            db: The SQLAlchemy database session for database operations.
            task: The AgentTask object that this plugin instance is processing.
        """
        self.db = db
        self.task = task

    @staticmethod
    @abstractmethod
    def get_id() -> str:
        """
        Returns a unique machine-readable identifier for the plugin.
        e.g., 'code_modifier', 'genealogy_researcher'.
        This ID is used to select and invoke the plugin.
        """
        pass

    @staticmethod
    @abstractmethod
    def get_name() -> str:
        """
        Returns a human-readable name for the plugin.
        e.g., 'Code Modifier', 'Genealogy Researcher'.
        This name is used for display in the UI.
        """
        pass

    @staticmethod
    @abstractmethod
    def get_description() -> str:
        """
        Returns a brief description of what the plugin does.
        This is used for display in the UI to help users understand the plugin's purpose.
        """
        pass

    @abstractmethod
    async def execute(self) -> dict:
        """
        The main execution method for the plugin.
        This asynchronous method should perform the plugin's primary action
        based on the information in `self.task`.

        Returns:
            A dictionary containing fields to update on the AgentTask model upon completion
            or error. Common keys include:
            - 'status': A models.TaskStatus enum value (e.g., AWAITING_REVIEW, APPLIED, ERROR).
            - 'llm_explanation': A string explanation from the LLM or the plugin itself.
            - 'proposed_diff': For code_modifier, the generated diff string.
            - 'test_status': A models.TestStatus enum value (if applicable).
            - 'test_results': Detailed test output (if applicable).
            - 'error_message': A string message if an error occurred.
        """
        pass
