from src.models.itinerary import Itinerary
from src.models.itinerary_item import ItineraryItem
from src.models.attraction import Attraction
from src.models.user import User
from src.models.base import db
from datetime import datetime, date
from typing import Dict, Any, List, Optional

def create_itinerary_with_items(user_id: int, selected_date: str, 
                               itinerary_items: List[Dict[str, Any]], 
                               title: Optional[str] = None,
                               notes: Optional[str] = None) -> tuple[bool, Dict[str, Any] | str]:
    """
    Create a new itinerary with multiple items
    
    Args:
        user_id (int): ID of the user
        selected_date (str): Selected date in ISO format (YYYY-MM-DD)
        itinerary_items (List[Dict]): List of itinerary items
        title (str, optional): Title for the itinerary
        notes (str, optional): General notes for the itinerary
        
    Returns:
        tuple: (success: bool, result: Dict or str)
    """
    try:
        print(f"ℹ️ Creating itinerary: user_id={user_id}, selected_date={selected_date}, items_count={len(itinerary_items)}")
        
        # Validate user exists
        user = User.query.get(user_id)
        if not user:
            return False, f"User with ID {user_id} not found"
        
        # Parse selected date
        try:
            parsed_date = datetime.fromisoformat(selected_date.split('T')[0]).date()
        except ValueError:
            return False, "Invalid selected_date format. Use ISO format (YYYY-MM-DD)"
        
        # Check if date is in the future
        if parsed_date < date.today():
            return False, "Selected date cannot be in the past"
        
        # Create new itinerary
        itinerary = Itinerary(
            user_id=user_id,
            selected_date=parsed_date,
            title=title,
            notes=notes
        )
        
        db.session.add(itinerary)
        db.session.flush()  # Get the itinerary ID
        
        # Add itinerary items
        for index, item_data in enumerate(itinerary_items):
            # Validate attraction exists
            attraction = Attraction.query.get(item_data['attraction_id'])
            if not attraction:
                db.session.rollback()
                return False, f"Attraction with ID {item_data['attraction_id']} not found"
            
            # Parse visit time
            try:
                visit_time_str = item_data['visit_time'].replace('Z', '+00:00')
                parsed_visit_time = datetime.fromisoformat(visit_time_str)
            except ValueError:
                db.session.rollback()
                return False, f"Invalid visit_time format for item {index + 1}. Use ISO format (YYYY-MM-DD HH:MM:SS)"
            
            # Check if visit time is on the selected date
            if parsed_visit_time.date() != parsed_date:
                db.session.rollback()
                return False, f"Visit time for item {index + 1} must be on the selected date"
            
            # Create itinerary item
            itinerary_item = ItineraryItem(
                itinerary_id=itinerary.id,
                attraction_id=item_data['attraction_id'],
                visit_time=parsed_visit_time,
                estimated_duration=item_data.get('estimated_duration'),
                notes=item_data.get('notes'),
                order_index=index
            )
            
            db.session.add(itinerary_item)
        
        db.session.commit()
        
        # Return the created itinerary with items
        result = itinerary.to_dict()
        print(f"ℹ️ Successfully created itinerary with ID: {itinerary.id}")
        
        return True, result
        
    except Exception as e:
        db.session.rollback()
        print(f'ℹ️ Lỗi khi tạo lịch trình: {e}')
        return False, str(e)

def get_user_itineraries(user_id: int) -> tuple[bool, List[Dict[str, Any]] | str]:
    """
    Get all itineraries for a user (excluding soft deleted ones)
    
    Args:
        user_id (int): ID of the user
        
    Returns:
        tuple: (success: bool, result: List[Dict] or str)
    """
    try:
        print(f"ℹ️ Getting itineraries for user_id: {user_id}")
        
        # Validate user exists
        user = User.query.get(user_id)
        if not user:
            return False, f"User with ID {user_id} not found"
        
        # Get itineraries ordered by selected date (excluding soft deleted ones)
        itineraries = Itinerary.query.filter_by(user_id=user_id, is_deleted=False)\
            .order_by(Itinerary.selected_date.asc()).all()
        
        result = [itinerary.to_dict() for itinerary in itineraries]
        print(f"ℹ️ Found {len(result)} itineraries for user {user_id}")
        
        return True, result
        
    except Exception as e:
        print(f'ℹ️ Lỗi khi lấy lịch trình: {e}')
        return False, str(e)

def get_itinerary_by_id(itinerary_id: int, user_id: int) -> tuple[bool, Dict[str, Any] | str]:
    """
    Get a specific itinerary by ID
    
    Args:
        itinerary_id (int): ID of the itinerary
        user_id (int): ID of the user (for authorization)
        
    Returns:
        tuple: (success: bool, result: Dict or str)
    """
    try:
        print(f"ℹ️ Getting itinerary: itinerary_id={itinerary_id}, user_id={user_id}")
        
        # Find the itinerary
        itinerary = Itinerary.query.get(itinerary_id)
        if not itinerary:
            return False, f"Itinerary with ID {itinerary_id} not found"
        
        # Check if user owns this itinerary
        if itinerary.user_id != user_id:
            return False, "You are not authorized to view this itinerary"
        
        result = itinerary.to_dict()
        print(f"ℹ️ Successfully retrieved itinerary with ID: {itinerary_id}")
        
        return True, result
        
    except Exception as e:
        print(f'ℹ️ Lỗi khi lấy lịch trình: {e}')
        return False, str(e)

def delete_itinerary(itinerary_id: int, user_id: int) -> tuple[bool, str]:
    """
    Delete (soft delete) an entire itinerary by setting isDelete=True
    Args:
        itinerary_id (int): ID of the itinerary
        user_id (int): ID of the user (for authorization)
    Returns:
        tuple: (success: bool, message: str)
    """
    try:
        print(f"ℹ️ Soft deleting itinerary: itinerary_id={itinerary_id}, user_id={user_id}")
        # Find the itinerary
        itinerary = Itinerary.query.get(itinerary_id)
        if not itinerary:
            return False, f"Itinerary with ID {itinerary_id} not found"
        # Check if user owns this itinerary
        if itinerary.user_id != user_id:
            return False, "You are not authorized to delete this itinerary"
        # Soft delete: set isDelete to True
        itinerary.is_deleted = True
        db.session.commit()
        print(f"ℹ️ Successfully soft deleted itinerary with ID: {itinerary_id}")
        return True, f"Successfully deleted itinerary with ID: {itinerary_id} (soft delete)"
    except Exception as e:
        db.session.rollback()
        print(f'ℹ️ Lỗi khi xóa mềm lịch trình: {e}')
        return False, str(e)

def update_itinerary_item(item_id: int, user_id: int, 
                         visit_time: Optional[str] = None,
                         estimated_duration: Optional[int] = None, 
                         notes: Optional[str] = None) -> tuple[bool, Dict[str, Any] | str]:
    """
    Update a specific itinerary item
    
    Args:
        item_id (int): ID of the itinerary item
        user_id (int): ID of the user (for authorization)
        visit_time (str, optional): New visit time in ISO format
        estimated_duration (int, optional): New estimated duration in minutes
        notes (str, optional): New notes
        
    Returns:
        tuple: (success: bool, result: Dict or str)
    """
    try:
        print(f"ℹ️ Updating itinerary item: item_id={item_id}, user_id={user_id}")
        
        # Find the itinerary item
        itinerary_item = ItineraryItem.query.get(item_id)
        if not itinerary_item:
            return False, f"Itinerary item with ID {item_id} not found"
        
        # Check if user owns this item's itinerary
        if itinerary_item.itinerary.user_id != user_id:
            return False, "You are not authorized to update this itinerary item"
        
        # Update fields if provided
        if visit_time is not None:
            try:
                visit_time_str = visit_time.replace('Z', '+00:00')
                parsed_visit_time = datetime.fromisoformat(visit_time_str)
                if parsed_visit_time.date() != itinerary_item.itinerary.selected_date:
                    return False, "Visit time must be on the itinerary's selected date"
                itinerary_item.visit_time = parsed_visit_time
            except ValueError:
                return False, "Invalid visit_time format. Use ISO format (YYYY-MM-DD HH:MM:SS)"
        
        if estimated_duration is not None:
            itinerary_item.estimated_duration = estimated_duration
            
        if notes is not None:
            itinerary_item.notes = notes
        
        # Save changes
        db.session.commit()
        
        result = itinerary_item.to_dict()
        print(f"ℹ️ Successfully updated itinerary item with ID: {item_id}")
        
        return True, result
        
    except Exception as e:
        db.session.rollback()
        print(f'ℹ️ Lỗi khi cập nhật lịch trình: {e}')
        return False, str(e)
