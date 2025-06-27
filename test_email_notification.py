#!/usr/bin/env python3
"""
Test script for actual email notification sending
This script tests the email sending functionality
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src import create_app
from src.models.base import db
from src.models.user import User
from src.models.itinerary import Itinerary
from src.models.notification import Notification
from src.services.notification_service import create_itinerary_reminder_notification, send_notification
from datetime import datetime, timedelta

def test_email_notification():
    """Test actual email notification sending"""
    app = create_app()
    
    with app.app_context():
        print("📧 Testing Email Notification System")
        print("=" * 50)
        
        # 1. Create a test user with real email
        print("\n1. Creating test user...")
        test_user = User(
            email="6451060041@st.utc2.edu.vn",  # Thay bằng email thật của bạn
            password_hash="123456",
            full_name="Test User",
            language_preference="en",
            is_verified=True
        )
        db.session.add(test_user)
        db.session.commit()
        print(f"✅ Created test user with ID: {test_user.user_id}")
        
        # 2. Create a test itinerary (for tomorrow)
        print("\n2. Creating test itinerary...")
        tomorrow = datetime.now().date() + timedelta(days=1)
        test_itinerary = Itinerary(
            user_id=test_user.user_id,
            selected_date=tomorrow,
            title="Test Itinerary",
            notes="This is a test itinerary for email notification testing"
        )
        db.session.add(test_itinerary)
        db.session.commit()
        print(f"✅ Created test itinerary with ID: {test_itinerary.id} for date: {tomorrow}")
        
        # 3. Create notification for immediate sending (5 seconds from now)
        print("\n3. Creating immediate notification...")
        immediate_time = datetime.now() + timedelta(seconds=5)
        
        notification = Notification(
            user_id=test_user.user_id,
            itinerary_id=test_itinerary.id,
            title=f"Test Email: Your itinerary for {tomorrow.strftime('%B %d, %Y')}",
            message=f"This is a test email notification for your itinerary on {tomorrow.strftime('%B %d, %Y')}. "
                   f"Please check your schedule!",
            notification_type='itinerary_reminder',
            scheduled_for=immediate_time
        )
        
        db.session.add(notification)
        db.session.commit()
        print(f"✅ Created notification with ID: {notification.id}")
        print(f"   Scheduled for: {immediate_time}")
        
        # 4. Test sending notification immediately
        print("\n4. Testing immediate email sending...")
        success = send_notification(notification)
        
        if success:
            print("✅ Email notification sent successfully!")
            print("   Check your email inbox (and spam folder)")
        else:
            print("❌ Failed to send email notification")
            print("   Check your email configuration in .env file")
        
        # 5. Check notification status
        print("\n5. Checking notification status...")
        updated_notification = Notification.query.get(notification.id)
        if updated_notification.sent_at:
            print(f"✅ Notification marked as sent at: {updated_notification.sent_at}")
        else:
            print("❌ Notification was not marked as sent")
        
        # 6. Cleanup
        print("\n6. Cleaning up test data...")
        Notification.query.filter_by(user_id=test_user.user_id).delete()
        Itinerary.query.filter_by(user_id=test_user.user_id).delete()
        User.query.filter_by(user_id=test_user.user_id).delete()
        db.session.commit()
        print("✅ Test data cleaned up")
        
        print("\n🎉 Email notification test completed!")

def test_manual_email():
    """Test manual email sending without database"""
    app = create_app()
    
    with app.app_context():
        print("\n📧 Testing Manual Email Sending")
        print("=" * 40)
        
        from src.services.email_service import send_notification_email
        
        # Test email configuration
        test_email = "your_email@gmail.com"  # Thay bằng email thật của bạn
        test_title = "Test Email from ScapeData"
        test_message = "This is a test email to verify your email configuration is working correctly."
        test_name = "Test User"
        
        print(f"Sending test email to: {test_email}")
        
        try:
            success = send_notification_email(test_email, test_title, test_message, test_name)
            
            if success:
                print("✅ Test email sent successfully!")
                print("   Check your email inbox (and spam folder)")
            else:
                print("❌ Failed to send test email")
                print("   Please check your email configuration")
                
        except Exception as e:
            print(f"❌ Error sending test email: {e}")
            print("   Please check your email configuration in .env file")

if __name__ == "__main__":
    print("🚀 Email Notification Test")
    print("=" * 50)
    
    # Check if user wants to test with real email
    print("\n⚠️  IMPORTANT: This test will send real emails!")
    print("   Make sure to update the email address in the script")
    print("   and configure your email settings in .env file")
    
    choice = input("\nDo you want to proceed? (y/n): ").lower().strip()
    
    if choice == 'y':
        # Test manual email first
        test_manual_email()
        
        # Test full notification system
        test_email_notification()
    else:
        print("Test cancelled.")
        print("\nTo run the test later:")
        print("1. Update email address in test_email_notification.py")
        print("2. Configure email settings in .env file")
        print("3. Run: python test_email_notification.py") 