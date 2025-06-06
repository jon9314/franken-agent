from abc import ABC, abstractmethod
from typing import List, Dict, Any # Import Any for flexible dict values
from app.db.models import Person # Assuming Person model is in app.db.models

class GenealogyTool(ABC):
    """Abstract base class for a tool that searches an external genealogy source."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key

    @property
    @abstractmethod
    def name(self) -> str:
        """The unique name of the tool (e.g., 'FamilySearch', 'FindAGrave.com')."""
        pass

    @property
    def is_configured(self) -> bool:
        """
        Returns True if the tool has the necessary configuration (e.g., API keys).
        Subclasses requiring API keys MUST override this to check self.api_key or other settings.
        """
        return True # Default for tools not needing specific config like FindAGrave scraper

    @abstractmethod
    async def search_person(self, person: Person) -> List[Dict[str, Any]]:
        """
        Searches for a person on the external source.

        Args:
            person: The Person object (SQLAlchemy model) from the database to research.

        Returns:
            A list of dictionaries, where each dictionary represents a potential
            finding from this specific tool. Each dict should ideally include:
            - 'data_field': The type of data this finding pertains to (e.g., 'birth_date', 
                            'death_place', 'mother_name', 'burial_place', 'existence_confirmation').
                            This helps the LLM synthesizer focus.
            - 'value': The actual data value found (e.g., "15 Mar 1920", "London, England").
            - 'source_url': A direct URL to the record or source page, if available.
            - 'citation': A pre-formatted or raw citation string from the tool, or elements to build one.
            - 'match_quality_notes': (Optional) Any notes from the tool about how good the match is 
                                     (e.g., "Exact name and birth year match", "Name similar, location matches").
            The 'source_name' will be automatically added by the plugin based on tool.name when findings are collected.
        """
        pass