from sqlalchemy.orm import Session
from loguru import logger
from io import StringIO
from typing import Dict, List

from gedcom.parser import Parser
from gedcom.element.element import Element

from app.db import models, crud

class GenealogyService:
    def __init__(self, db: Session):
        self.db = db

    def parse_and_store_gedcom(self, file_content_str: str, file_name: str, owner_id: int) -> models.FamilyTree:
        logger.info(f"Starting GEDCOM parsing for file: '{file_name}' by owner_id: {owner_id}")
        
        gedcom_lines = file_content_str.splitlines()
        parser = Parser()
        
        try:
            root_child_elements: List[Element] = parser.parse_lines(gedcom_lines)
        except Exception as e:
            logger.error(f"Error parsing GEDCOM lines for file '{file_name}': {e}", exc_info=True)
            raise ValueError(f"Could not parse GEDCOM file '{file_name}'. It might be malformed or not a valid GEDCOM file.")

        if not root_child_elements:
            logger.warning(f"GEDCOM file '{file_name}' appears to be empty or invalid after parsing (no root elements).")
            raise ValueError(f"GEDCOM file '{file_name}' could not be parsed or yielded no data.")

        db_tree = crud.create_family_tree(self.db, file_name=file_name, owner_id=owner_id)
        
        person_map: Dict[str, models.Person] = {} 
        
        for element in root_child_elements:
            if element.get_tag() == "INDI":
                gedcom_id = element.get_pointer()
                if not gedcom_id:
                    logger.warning(f"Skipping INDI record without a pointer in '{file_name}'.")
                    continue

                name_parts = element.get_name()
                
                first_name = name_parts[0].strip() if name_parts and len(name_parts) > 0 and name_parts[0] else None
                last_name = name_parts[1].strip() if name_parts and len(name_parts) > 1 and name_parts[1] else None

                sex = element.get_gender() or "U"

                birth_data = element.get_birth_data()
                birth_date_str = birth_data[0].strip() if birth_data and birth_data[0] else None
                birth_place_str = birth_data[1].strip() if birth_data and birth_data[1] else None

                death_data = element.get_death_data()
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
                    "tree_id": db_tree.id
                }
                
                db_person = models.Person(**person_data_for_model)
                self.db.add(db_person)
                person_map[gedcom_id] = db_person
        
        try:
            self.db.commit() 
        except Exception as e:
            self.db.rollback()
            logger.error(f"Database error committing persons for tree '{file_name}': {e}", exc_info=True)
            raise
            
        for person_obj in person_map.values():
            self.db.refresh(person_obj)
        logger.info(f"Created and committed {len(person_map)} person records for tree_id: {db_tree.id}.")

        family_map: Dict[str, models.Family] = {}
        for element in root_child_elements:
            if element.get_tag() == "FAM":
                gedcom_id = element.get_pointer()
                if not gedcom_id:
                    logger.warning(f"Skipping FAM record without a pointer in '{file_name}'.")
                    continue

                family_data_for_model = {
                    "gedcom_id": gedcom_id,
                    "tree_id": db_tree.id
                }
                
                husband_ptr = element.get_husband()
                if husband_ptr and husband_ptr in person_map:
                    family_data_for_model["husband_id"] = person_map[husband_ptr].id

                wife_ptr = element.get_wife()
                if wife_ptr and wife_ptr in person_map:
                    family_data_for_model["wife_id"] = person_map[wife_ptr].id
                
                db_family = models.Family(**family_data_for_model)
                self.db.add(db_family)
                try:
                    self.db.flush() 
                except Exception as e:
                    self.db.rollback()
                    logger.error(f"Database error flushing family '{gedcom_id}' for tree '{file_name}': {e}", exc_info=True)
                    continue

                for child_element in element.get_child_elements():
                    child_ptr = child_element.get_value()
                    if child_ptr in person_map:
                        db_family.children.append(person_map[child_ptr])
                
                family_map[gedcom_id] = db_family

        logger.info(f"Processed {len(family_map)} FAM records for tree_id: {db_tree.id}. Committing families...")
        try:
            self.db.commit()
        except Exception as e:
            self.db.rollback()
            logger.error(f"Database error committing families for tree '{file_name}': {e}", exc_info=True)
            raise

        self.db.refresh(db_tree)
        logger.info(f"GEDCOM parsing and storage complete for file: '{file_name}', Tree ID: {db_tree.id}")
        return db_tree
