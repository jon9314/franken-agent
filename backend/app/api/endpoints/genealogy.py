from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, status, Body
from sqlalchemy.orm import Session
from typing import List, Any
from datetime import datetime # For updating reviewed_at timestamp
from loguru import logger # For logging

from app.core.dependencies import get_db, get_current_active_user, get_current_admin_user
from app.db import schemas, models, crud
from app.services.genealogy_service import GenealogyService

router = APIRouter()

@router.post("/trees/upload", response_model=schemas.FamilyTreeSimple, status_code=status.HTTP_201_CREATED)
async def upload_new_gedcom_tree( # Renamed for clarity
    *,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user), # Any logged-in user can upload
    file: UploadFile = File(..., description="A GEDCOM (.ged) file representing a family tree.")
):
    """
    Upload a GEDCOM (.ged) file. The system will parse it and store it as a new family tree,
    associated with the currently authenticated user.
    """
    if not file.filename or not file.filename.lower().endswith(".ged"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Invalid file type. Please upload a valid .ged (GEDCOM) file."
        )
    
    logger.info(f"User {current_user.email} attempting to upload GEDCOM file: {file.filename}")
    file_content_bytes = await file.read()
    
    try:
        # Attempt to decode with UTF-8, then fall back to Latin-1 (common for older GEDCOMs)
        gedcom_string = file_content_bytes.decode('utf-8')
    except UnicodeDecodeError:
        try:
            gedcom_string = file_content_bytes.decode('latin-1')
            logger.info(f"Successfully decoded '{file.filename}' using latin-1 after UTF-8 failed.")
        except UnicodeDecodeError:
            logger.error(f"Failed to decode '{file.filename}' with UTF-8 or Latin-1 for user {current_user.email}.")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, 
                detail="Could not decode file content. Please ensure it is a valid GEDCOM file with UTF-8 or Latin-1 encoding."
            )

    if not gedcom_string.strip(): # Check if file content is empty after decoding
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded GEDCOM file is empty or contains no parsable content.")

    service = GenealogyService(db)
    try:
        new_tree = service.parse_and_store_gedcom(
            file_content_str=gedcom_string,
            file_name=file.filename,
            owner_id=current_user.id
        )
        logger.info(f"Successfully created FamilyTree ID {new_tree.id} for user {current_user.email} from file {file.filename}")
        return new_tree
    except ValueError as ve: # Catch specific errors from the service (e.g., parsing issues)
         logger.warning(f"ValueError during GEDCOM processing for {file.filename} by user {current_user.email}: {ve}")
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.error(f"Unexpected error processing GEDCOM upload '{file.filename}' for user {current_user.email}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred while processing the GEDCOM file.")


@router.get("/trees", response_model=List[schemas.FamilyTreeSimple])
def get_list_of_user_family_trees( # Renamed for clarity
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user),
    skip: int = 0,
    limit: int = 100
):
    """Get a list of all family trees uploaded by the current authenticated user."""
    return crud.get_family_trees_by_owner(db, owner_id=current_user.id, skip=skip, limit=limit)


@router.get("/trees/{tree_id}", response_model=schemas.FamilyTree) # Returns full tree with persons/families
def get_specific_family_tree_details( # Renamed for clarity
    tree_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user)
):
    """
    Get the full details of a specific family tree, including all persons and families.
    Ensures the tree belongs to the authenticated user.
    """
    tree = crud.get_family_tree_with_details(db, tree_id=tree_id, owner_id=current_user.id)
    if not tree:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Family tree not found or you do not have permission to view it.")
    return tree

@router.get("/people/{person_id}/findings", response_model=List[schemas.ResearchFinding])
def get_research_findings_for_person( # Renamed for clarity
    person_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_active_user), # Any logged-in user can see findings for trees they own
):
    """
    Get all research findings for a specific person.
    Ensures the current user owns the family tree this person belongs to.
    """
    person = crud.get_person_by_id(db, person_id=person_id)
    if not person:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Person not found.")
    
    # Verify ownership of the tree this person belongs to
    # This check relies on the Person model having a tree_id and FamilyTree model having an owner_id
    tree = crud.get_family_tree_with_details(db, tree_id=person.tree_id, owner_id=current_user.id)
    if not tree: # If tree is None, it means it either doesn't exist or doesn't belong to current_user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view findings for this person as you do not own the tree.")
    
    return crud.get_research_findings_for_person(db, person_id=person_id)

# Admin-only endpoints for reviewing findings
@router.post("/admin/findings/{finding_id}/accept", response_model=schemas.ResearchFinding, tags=["Admin & Agent Management"])
def admin_accept_research_finding( # Renamed for clarity and admin context
    finding_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user), # Admin only
):
    """
    ADMIN ONLY: Accept a research finding. This updates the associated person's record
    with the suggested value and marks the finding as 'ACCEPTED'.
    """
    finding = crud.get_research_finding_by_id(db, finding_id=finding_id)
    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research finding not found.")
    
    # Admin can accept findings for any tree. If ownership check for non-superadmin was needed:
    # if finding.person.tree.owner_id != current_user.id:
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized.")

    if finding.status != models.FindingStatus.UNVERIFIED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Finding is not UNVERIFIED. Current status: {finding.status.value}")

    person_to_update = crud.get_person_by_id(db, person_id=finding.person_id)
    if not person_to_update: # Should not happen if finding exists and FK is valid
        logger.error(f"Data integrity issue: Person ID {finding.person_id} for finding ID {finding.id} not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Associated person for this finding not found. Data integrity issue.")

    # Apply the change to the person record
    if hasattr(person_to_update, finding.data_field):
        logger.info(f"Admin {current_user.email} accepting finding {finding.id}: Setting Person.{finding.data_field} from '{getattr(person_to_update, finding.data_field)}' to '{finding.suggested_value}'.")
        setattr(person_to_update, finding.data_field, finding.suggested_value)
        db.add(person_to_update) # Mark person as dirty for session to save changes
    else:
        logger.warning(f"Data field '{finding.data_field}' not found on Person model for finding {finding.id} during accept by admin {current_user.email}. Cannot apply change to person.")
        # Depending on policy, you might still mark finding as ACCEPTED if admin deems data useful elsewhere
        # Or raise an error. For now, let's allow status update but log the attribute issue.
        # raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid data field '{finding.data_field}' specified in finding.")
    
    # Update the finding status
    finding_update_data = {
        "status": models.FindingStatus.ACCEPTED,
        "reviewed_at": datetime.now(datetime.timezone.utc), # Use timezone aware datetime
        "reviewed_by_id": current_user.id
    }
    updated_finding = crud.update_research_finding(db, db_finding=finding, finding_update_data=finding_update_data)
    
    return updated_finding

@router.post("/admin/findings/{finding_id}/reject", response_model=schemas.ResearchFinding, tags=["Admin & Agent Management"])
def admin_reject_research_finding( # Renamed for clarity and admin context
    finding_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user), # Admin only
):
    """ADMIN ONLY: Reject a research finding. Marks the finding as 'REJECTED'."""
    finding = crud.get_research_finding_by_id(db, finding_id=finding_id)
    if not finding:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Research finding not found.")

    # Admin can reject findings for any tree.
    if finding.status != models.FindingStatus.UNVERIFIED:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Finding is not UNVERIFIED. Current status: {finding.status.value}")

    finding_update_data = {
        "status": models.FindingStatus.REJECTED,
        "reviewed_at": datetime.now(datetime.timezone.utc),
        "reviewed_by_id": current_user.id
    }
    updated_finding = crud.update_research_finding(db, db_finding=finding, finding_update_data=finding_update_data)
    logger.info(f"Admin {current_user.email} rejected finding {finding.id}.")
    return updated_finding

# Endpoint for admins to see all unverified findings across all trees.
@router.get("/admin/findings/unverified", response_model=List[schemas.ResearchFinding], tags=["Admin & Agent Management"])
def admin_get_all_unverified_findings(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_admin_user),
    skip: int = 0,
    limit: int = 50 # Paginate results
):
    """ADMIN ONLY: Get a list of all research findings with UNVERIFIED status across all family trees."""
    return crud.get_all_unverified_research_findings(db, skip=skip, limit=limit)