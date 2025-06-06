from sqlalchemy.orm import Session
from gedcom import Gedcom, Element # From python-gedcom library
from loguru import logger
from io import StringIO
from typing import Dict # For type hinting

from app.db import models, crud # Ensure crud is available for database operations

class GenealogyService:
    def __init__(self, db: Session):
        self.db = db

    def parse_and_store_gedcom(self, file_content_str: str, file_name: str, owner_id: int) -> models.FamilyTree:
        logger.info(f"Starting GEDCOM parsing for file: '{file_name}' by owner_id: {owner_id}")
        
        # The python-gedcom library expects a list of lines for its parse_lines method.
        gedcom_lines = file_content_str.splitlines()
        parser = Gedcom()
        
        # root_child_elements will contain all top-level elements (HEAD, INDI, FAM, TRLR etc.)
        try:
            root_child_elements: List[Element] = parser.parse_lines(gedcom_lines)
        except Exception as e: # Catch potential parsing errors from python-gedcom
            logger.error(f"Error parsing GEDCOM lines for file '{file_name}': {e}", exc_info=True)
            raise ValueError(f"Could not parse GEDCOM file '{file_name}'. It might be malformed or not a valid GEDCOM file.")

        if not root_child_elements:
            logger.warning(f"GEDCOM file '{file_name}' appears to be empty or invalid after parsing (no root elements).")
            raise ValueError(f"GEDCOM file '{file_name}' could not be parsed or yielded no data.")

        # Create the main FamilyTree record in the database
        db_tree = crud.create_family_tree(self.db, file_name=file_name, owner_id=owner_id)
        
        # Using a dictionary to map GEDCOM pointers (e.g., @I1@) to newly created DB Person objects.
        # This is crucial for linking spouses and children in the second pass.
        person_map: Dict[str, models.Person] = {} 
        
        # --- First Pass: Create all Person records ---
        for element in root_child_elements:
            if element.get_tag() == "INDI": # Individual record
                gedcom_id = element.get_pointer() # e.g., "@I1@"
                if not gedcom_id:
                    logger.warning(f"Skipping INDI record without a pointer in '{file_name}'.")
                    continue

                name_parts = element.get_name() # Returns (first, last) tuple
                
                first_name = name_parts[0].strip() if name_parts and len(name_parts) > 0 and name_parts[0] else None
                last_name = name_parts[1].strip() if name_parts and len(name_parts) > 1 and name_parts[1] else None

                sex = element.get_gender() or "U" # Default to Unknown if not specified

                birth_data = element.get_birth_data() # Returns (date_str, place_str) tuple
                birth_date_str = birth_data[0].strip() if birth_data and birth_data[0] else None
                birth_place_str = birth_data[1].strip() if birth_data and birth_data[1] else None

                death_data = element.get_death_data() # Returns (date_str, place_str) tuple
                death_date_str = death_data[0].strip() if death_data and death_data[0] else None
                death_place_str = death_data[1].strip() if death_data and death_data[1] else None

                person_data_for_model = {
                    "gedcom_id": gedcom_id,
                    "first_name": first_name,
                    "last_name": last_name,
                    "sex": sex,
                    "birth_date": birth_date_str,
                    "birth_place": birth_place_str,
                    "death_date": death_date_str,
                    "death_place": death_place_str,
                    "tree_id": db_tree.id # Link to the parent FamilyTree
                }
                
                db_person = models.Person(**person_data_for_model)
                self.db.add(db_person)
                person_map[gedcom_id] = db_person # Store for linking in the second pass
        
        # Commit all persons to get their database IDs, essential for relationship linking.
        try:
            self.db.commit() 
        except Exception as e:
            self.db.rollback()
            logger.error(f"Database error committing persons for tree '{file_name}': {e}", exc_info=True)
            raise
            
        for person_obj in person_map.values(): # Refresh objects to ensure relationships can be appended.
            self.db.refresh(person_obj)
        logger.info(f"Created and committed {len(person_map)} person records for tree_id: {db_tree.id}.")

        # --- Second Pass: Create Family records and link individuals ---
        family_map: Dict[str, models.Family] = {}
        for element in root_child_elements:
            if element.get_tag() == "FAM": # Family record
                gedcom_id = element.get_pointer()
                if not gedcom_id:
                    logger.warning(f"Skipping FAM record without a pointer in '{file_name}'.")
                    continue

                family_data_for_model = {
                    "gedcom_id": gedcom_id,
                    "tree_id": db_tree.id # Link to the parent FamilyTree
                }
                
                husband_ptr = element.get_husband() # Returns INDI pointer (e.g., @I1@)
                if husband_ptr and husband_ptr in person_map:
                    family_data_for_model["husband_id"] = person_map[husband_ptr].id

                wife_ptr = element.get_wife() # Returns INDI pointer
                if wife_ptr and wife_ptr in person_map:
                    family_data_for_model["wife_id"] = person_map[wife_ptr].id
                
                db_family = models.Family(**family_data_for_model)
                self.db.add(db_family)
                # Must flush here to get db_family.id before appending children to association table
                try:
                    self.db.flush() 
                except Exception as e:
                    self.db.rollback()
                    logger.error(f"Database error flushing family '{gedcom_id}' for tree '{file_name}': {e}", exc_info=True)
                    # Potentially skip this family and continue, or raise
                    continue


                # Link children to this family
                for child_element in element.get_child_elements(): # These are sub-elements of FAM like '1 CHIL @I3@'
                    child_ptr = child_element.get_value() # This gets the INDI pointer (e.g., @I3@)
                    if child_ptr in person_map:
                        # SQLAlchemy handles the association table writes via the relationship.append
                        db_family.children.append(person_map[child_ptr])
                
                family_map[gedcom_id] = db_family

        logger.info(f"Processed {len(family_map)} FAM records for tree_id: {db_tree.id}. Committing families...")
        try:
            self.db.commit() # Commit all families and their child relationships
        except Exception as e:
            self.db.rollback()
            logger.error(f"Database error committing families for tree '{file_name}': {e}", exc_info=True)
            raise

        self.db.refresh(db_tree) # Refresh the main tree object to load all its relationships
        logger.info(f"GEDCOM parsing and storage complete for file: '{file_name}', Tree ID: {db_tree.id}")
        return db_tree