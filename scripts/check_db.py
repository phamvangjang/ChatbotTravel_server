import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database import db
from app.models.models import User, Location, UserPreference, Itinerary
from app import create_app

def check_database():
    app = create_app()
    with app.app_context():
        print("\n=== KIỂM TRA DATABASE ===\n")
        
        # Kiểm tra Users
        print("=== USERS ===")
        users = User.query.all()
        print(f"Tổng số users: {len(users)}")
        for user in users:
            print(f"- {user.email} ({user.full_name})")
        
        # Kiểm tra Locations
        print("\n=== LOCATIONS ===")
        locations = Location.query.all()
        print(f"Tổng số địa điểm: {len(locations)}")
        for loc in locations:
            print(f"- {loc.name}")
            print(f"  Mô tả: {loc.description[:100]}...")
            print(f"  Đánh giá: {loc.ratings}")
            if hasattr(loc, 'features') and loc.features:
                print(f"  Hoạt động: {loc.features.get('activities', [])}")
                print(f"  Thời điểm tốt nhất: {loc.features.get('best_time', [])}")
            print()
        
        # Kiểm tra User Preferences
        print("\n=== USER PREFERENCES ===")
        prefs = UserPreference.query.all()
        print(f"Tổng số preferences: {len(prefs)}")
        for pref in prefs:
            user = User.query.get(pref.user_id)
            print(f"- User: {user.email}")
            print(f"  Hoạt động yêu thích: {pref.activity_preferences}")
            print(f"  Ngân sách: {pref.budget_range}")
            print()
        
        # Kiểm tra Itineraries
        print("\n=== ITINERARIES ===")
        itineraries = Itinerary.query.all()
        print(f"Tổng số lịch trình: {len(itineraries)}")
        for itin in itineraries:
            user = User.query.get(itin.user_id)
            print(f"- User: {user.email}")
            print(f"  Điểm đến: {itin.destination}")
            print(f"  Thời gian: {itin.start_date} -> {itin.end_date}")
            if itin.activities:
                print(f"  Hoạt động: {itin.activities}")
            print()

if __name__ == "__main__":
    check_database() 