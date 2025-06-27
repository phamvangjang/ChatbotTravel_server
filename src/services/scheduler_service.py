import threading
import time
from datetime import datetime
from src.services.notification_service import get_pending_notifications, send_notification
from src.services.Itinerary_service import create_itinerary_with_items
from src.services.notification_service import create_itinerary_reminder_notification

class NotificationScheduler:
    def __init__(self):
        self.running = False
        self.thread = None
        self.check_interval = 60  # Check every 60 seconds
        
    def start(self):
        """Start the notification scheduler"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.thread.start()
        print("🔔 Notification scheduler started")
        
    def stop(self):
        """Stop the notification scheduler"""
        self.running = False
        if self.thread:
            self.thread.join()
        print("🔔 Notification scheduler stopped")
        
    def _run_scheduler(self):
        """Main scheduler loop"""
        while self.running:
            try:
                self._process_pending_notifications()
                time.sleep(self.check_interval)
            except Exception as e:
                print(f"Error in notification scheduler: {e}")
                time.sleep(self.check_interval)
                
    def _process_pending_notifications(self):
        """Process all pending notifications"""
        try:
            pending_notifications = get_pending_notifications()
            
            for notification in pending_notifications:
                try:
                    success = send_notification(notification)
                    if success:
                        print(f"✅ Sent notification {notification.id} to user {notification.user_id}")
                    else:
                        print(f"❌ Failed to send notification {notification.id}")
                except Exception as e:
                    print(f"Error sending notification {notification.id}: {e}")
                    
        except Exception as e:
            print(f"Error processing pending notifications: {e}")

# Global scheduler instance
notification_scheduler = NotificationScheduler()

def start_notification_scheduler():
    """Start the notification scheduler"""
    notification_scheduler.start()

def stop_notification_scheduler():
    """Stop the notification scheduler"""
    notification_scheduler.stop()

def create_itinerary_with_reminder(user_id: int, selected_date: str, 
                                 itinerary_items: list, title: str = None, 
                                 notes: str = None) -> tuple[bool, dict | str]:
    """
    Create itinerary and automatically schedule a reminder notification
    
    Args:
        user_id (int): ID of the user
        selected_date (str): Selected date in ISO format
        itinerary_items (list): List of itinerary items
        title (str, optional): Itinerary title
        notes (str, optional): Itinerary notes
        
    Returns:
        tuple: (success: bool, result: dict or str)
    """
    try:
        # First create the itinerary
        success, result = create_itinerary_with_items(
            user_id=user_id,
            selected_date=selected_date,
            itinerary_items=itinerary_items,
            title=title,
            notes=notes
        )
        
        if not success:
            return False, result
        
        # If itinerary creation successful, schedule reminder notification
        itinerary_id = result['id']
        reminder_success, reminder_message = create_itinerary_reminder_notification(itinerary_id)
        
        if reminder_success:
            print(f"✅ Scheduled reminder notification for itinerary {itinerary_id}")
        else:
            print(f"⚠️ Warning: Could not schedule reminder for itinerary {itinerary_id}: {reminder_message}")
        
        return True, result
        
    except Exception as e:
        return False, str(e) 