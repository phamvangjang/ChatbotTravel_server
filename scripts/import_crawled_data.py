import sys
import os
import json
from datetime import datetime
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.models.database import db
from app.models.models import Location, VietnamRegion, LocationCategory

def convert_to_location_model(data: dict) -> Location:
    """Convert crawled data to Location model"""
    
    # Map region names
    region_map = {
        "Nam": VietnamRegion.SOUTH,
        "Bắc": VietnamRegion.NORTH,
        "Trung": VietnamRegion.CENTRAL
    }
    
    # Create categories list
    categories = []
    if "Giải trí" in str(data.get("attractions", [])):
        categories.append(LocationCategory.URBAN)
    if "Di tích lịch sử" in str(data.get("attractions", [])):
        categories.append(LocationCategory.HISTORICAL)
    if "Văn hóa" in str(data):
        categories.append(LocationCategory.CULTURAL)
    
    # Create location object
    location = Location(
        name=data["name"],
        region=region_map[data["region"]],
        categories=categories,
        description=data["description"],
        
        # Weather information
        weather=data["weather"],
        
        # Transportation details
        transportation=data["transportation"],
        
        # Food and dining
        cuisine=data["cuisine"],
        
        # Points of interest
        attractions=data["attractions"],
        
        # Shopping information
        shopping=data["shopping"],
        
        # Suburban tourism
        suburban_tourism=data["suburban_tourism"],
        
        # Best months to visit (extract from weather data)
        best_months=["12", "1", "2", "3"] if "mùa khô" in data["weather"]["dry_season"].lower() else [],
        
        # Peak seasons
        peak_season={
            "domestic": ["6", "7", "8"],  # Summer vacation
            "international": ["12", "1", "2"]  # Winter escape
        },
        
        # Budget category (based on accommodation and food prices)
        budget_category="mid-range",
        
        # Additional metadata
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    return location

def import_crawled_data(json_file: str):
    """Import crawled data into database"""
    app = create_app()
    
    with app.app_context():
        # Load JSON data
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Convert to Location model
        location = convert_to_location_model(data)
        
        # Check if location already exists
        existing = Location.query.filter_by(name=location.name).first()
        if existing:
            # Update existing location
            for key, value in location.__dict__.items():
                if not key.startswith('_'):
                    setattr(existing, key, value)
            db.session.commit()
            print(f"Updated existing location: {location.name}")
        else:
            # Add new location
            db.session.add(location)
            db.session.commit()
            print(f"Added new location: {location.name}")

def main():
    # Create data directory if it doesn't exist
    os.makedirs('data', exist_ok=True)
    
    # Import HCMC data
    json_file = 'data/hcmc_travel_data.json'
    if os.path.exists(json_file):
        import_crawled_data(json_file)
        print("Data import completed successfully!")
    else:
        print(f"Error: {json_file} not found. Please run the crawler first.")

if __name__ == "__main__":
    main() 