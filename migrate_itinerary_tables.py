#!/usr/bin/env python3
"""
Migration script to update itinerary tables structure
This script will:
1. Create new Itineraries table
2. Update ItineraryItems table structure
3. Migrate existing data if any
4. Preserve all existing data
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.models.base import db
from src import create_app
from src.models.itinerary import Itinerary
from src.models.itinerary_item import ItineraryItem
from src.models.user import User
from src.models.attraction import Attraction
from datetime import datetime
import logging
from sqlalchemy import text

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create app instance
app = create_app()

def check_existing_tables():
    """Check if tables exist and their current structure"""
    try:
        with app.app_context():
            # Check if ItineraryItems table exists
            result = db.session.execute(text("""
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = 'ItineraryItems'
            """)).fetchone()
            
            if result and result.count > 0:
                logger.info("✅ ItineraryItems table exists")
                
                # Check current structure
                columns = db.session.execute(text("""
                    SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
                    FROM information_schema.columns 
                    WHERE table_schema = DATABASE() 
                    AND table_name = 'ItineraryItems'
                    ORDER BY ORDINAL_POSITION
                """)).fetchall()
                
                logger.info("Current ItineraryItems columns:")
                for col in columns:
                    logger.info(f"  - {col.COLUMN_NAME}: {col.DATA_TYPE} ({'NULL' if col.IS_NULLABLE == 'YES' else 'NOT NULL'})")
                
                return True
            else:
                logger.info("❌ ItineraryItems table does not exist")
                return False
                
    except Exception as e:
        logger.error(f"Error checking existing tables: {e}")
        return False

def create_itineraries_table():
    """Create the new Itineraries table"""
    try:
        with app.app_context():
            # Check if Itineraries table already exists
            result = db.session.execute(text("""
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = 'Itineraries'
            """)).fetchone()
            
            if result and result.count > 0:
                logger.info("✅ Itineraries table already exists")
                return True
            
            # Create Itineraries table
            db.session.execute(text("""
                CREATE TABLE Itineraries (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id INT NOT NULL,
                    selected_date DATE NOT NULL,
                    title VARCHAR(255),
                    notes TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE,
                    INDEX idx_user_date (user_id, selected_date)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """))
            
            logger.info("✅ Created Itineraries table successfully")
            return True
            
    except Exception as e:
        logger.error(f"Error creating Itineraries table: {e}")
        return False

def backup_existing_data():
    """Backup existing ItineraryItems data if any"""
    try:
        with app.app_context():
            # Check if there's existing data
            count = db.session.execute(text("SELECT COUNT(*) as count FROM ItineraryItems")).fetchone()
            
            if count and count.count > 0:
                logger.info(f"📦 Found {count.count} existing ItineraryItems, backing up...")
                
                # Create backup table
                db.session.execute(text("""
                    CREATE TABLE ItineraryItems_backup AS 
                    SELECT * FROM ItineraryItems
                """))
                
                logger.info("✅ Created backup table: ItineraryItems_backup")
                return True
            else:
                logger.info("ℹ️ No existing data to backup")
                return True
                
    except Exception as e:
        logger.error(f"Error backing up data: {e}")
        return False

def migrate_existing_data():
    """Migrate existing data to new structure"""
    try:
        with app.app_context():
            # Check if backup table exists
            result = db.session.execute(text("""
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_schema = DATABASE() 
                AND table_name = 'ItineraryItems_backup'
            """)).fetchone()
            
            if not result or result.count == 0:
                logger.info("ℹ️ No backup data to migrate")
                return True
            
            # Get backup data
            backup_items = db.session.execute(text("SELECT * FROM ItineraryItems_backup")).fetchall()
            
            if not backup_items:
                logger.info("ℹ️ No data in backup table")
                return True
            
            logger.info(f"🔄 Migrating {len(backup_items)} items...")
            
            # Group items by user_id and visit_time date
            user_date_groups = {}
            for item in backup_items:
                visit_date = item.visit_time.date() if item.visit_time else datetime.now().date()
                key = (item.user_id, visit_date)
                
                if key not in user_date_groups:
                    user_date_groups[key] = []
                user_date_groups[key].append(item)
            
            # Create itineraries and migrate items
            for (user_id, visit_date), items in user_date_groups.items():
                # Create itinerary
                itinerary = Itinerary(
                    user_id=user_id,
                    selected_date=visit_date,
                    title=f"Migrated Itinerary - {visit_date}",
                    notes="Migrated from old structure"
                )
                db.session.add(itinerary)
                db.session.flush()  # Get itinerary ID
                
                # Migrate items
                for index, item in enumerate(items):
                    itinerary_item = ItineraryItem(
                        itinerary_id=itinerary.id,
                        attraction_id=item.attraction_id,
                        visit_time=item.visit_time,
                        estimated_duration=item.estimated_duration,
                        notes=item.notes,
                        order_index=index,
                        created_at=item.created_at
                    )
                    db.session.add(itinerary_item)
            
            db.session.commit()
            logger.info(f"✅ Successfully migrated {len(backup_items)} items to new structure")
            return True
            
    except Exception as e:
        logger.error(f"Error migrating data: {e}")
        db.session.rollback()
        return False

def update_itinerary_items_table():
    """Update ItineraryItems table structure"""
    try:
        with app.app_context():
            # Check current structure
            columns = db.session.execute(text("""
                SELECT COLUMN_NAME
                FROM information_schema.columns 
                WHERE table_schema = DATABASE() 
                AND table_name = 'ItineraryItems'
                ORDER BY ORDINAL_POSITION
            """)).fetchall()
            
            column_names = [col.COLUMN_NAME for col in columns]
            
            # Add new columns if they don't exist
            if 'itinerary_id' not in column_names:
                logger.info("➕ Adding itinerary_id column...")
                db.session.execute(text("""
                    ALTER TABLE ItineraryItems 
                    ADD COLUMN itinerary_id INT,
                    ADD FOREIGN KEY (itinerary_id) REFERENCES Itineraries(id) ON DELETE CASCADE
                """))
                logger.info("✅ Added itinerary_id column")
            
            if 'order_index' not in column_names:
                logger.info("➕ Adding order_index column...")
                db.session.execute(text("""
                    ALTER TABLE ItineraryItems 
                    ADD COLUMN order_index INT DEFAULT 0
                """))
                logger.info("✅ Added order_index column")
            
            # Remove old user_id column if it exists (regardless of backup data)
            if 'user_id' in column_names:
                logger.info("🗑️ Removing old user_id column...")
                try:
                    # Drop foreign key constraint first
                    db.session.execute(text("""
                        ALTER TABLE ItineraryItems 
                        DROP FOREIGN KEY itineraryitems_ibfk_1
                    """))
                    logger.info("✅ Dropped old foreign key constraint")
                except Exception as e:
                    logger.info(f"ℹ️ Foreign key constraint already dropped or doesn't exist: {e}")
                
                try:
                    # Drop the user_id column
                    db.session.execute(text("""
                        ALTER TABLE ItineraryItems 
                        DROP COLUMN user_id
                    """))
                    logger.info("✅ Removed old user_id column")
                except Exception as e:
                    logger.error(f"❌ Failed to remove user_id column: {e}")
                    return False
            
            # Update foreign key constraint for attraction_id
            try:
                db.session.execute(text("""
                    ALTER TABLE ItineraryItems 
                    DROP FOREIGN KEY itineraryitems_ibfk_2
                """))
                logger.info("✅ Dropped old attraction foreign key")
            except Exception as e:
                logger.info(f"ℹ️ Attraction foreign key already dropped or doesn't exist: {e}")
            
            try:
                db.session.execute(text("""
                    ALTER TABLE ItineraryItems 
                    ADD CONSTRAINT fk_itinerary_items_attraction 
                    FOREIGN KEY (attraction_id) REFERENCES Attractions(id) ON DELETE CASCADE
                """))
                logger.info("✅ Added new attraction foreign key")
            except Exception as e:
                logger.info(f"ℹ️ Attraction foreign key already exists: {e}")
            
            # Add indexes for better performance
            try:
                db.session.execute(text("""
                    CREATE INDEX idx_itinerary_items_itinerary 
                    ON ItineraryItems(itinerary_id)
                """))
                logger.info("✅ Added itinerary index")
            except Exception as e:
                logger.info(f"ℹ️ Itinerary index already exists: {e}")
            
            try:
                db.session.execute(text("""
                    CREATE INDEX idx_itinerary_items_order 
                    ON ItineraryItems(itinerary_id, order_index)
                """))
                logger.info("✅ Added order index")
            except Exception as e:
                logger.info(f"ℹ️ Order index already exists: {e}")
            
            logger.info("✅ Updated ItineraryItems table structure")
            return True
            
    except Exception as e:
        logger.error(f"Error updating ItineraryItems table: {e}")
        return False

def cleanup_backup():
    """Clean up backup table after successful migration"""
    try:
        with app.app_context():
            db.session.execute(text("DROP TABLE IF EXISTS ItineraryItems_backup"))
            logger.info("✅ Cleaned up backup table")
            return True
    except Exception as e:
        logger.error(f"Error cleaning up backup: {e}")
        return False

def run_migration():
    """Run the complete migration process"""
    logger.info("🚀 Starting itinerary tables migration...")
    
    try:
        # Step 1: Check existing structure
        logger.info("📋 Step 1: Checking existing tables...")
        check_existing_tables()
        
        # Step 2: Create Itineraries table
        logger.info("📋 Step 2: Creating Itineraries table...")
        if not create_itineraries_table():
            logger.error("❌ Failed to create Itineraries table")
            return False
        
        # Step 3: Backup existing data
        logger.info("📋 Step 3: Backing up existing data...")
        if not backup_existing_data():
            logger.error("❌ Failed to backup existing data")
            return False
        
        # Step 4: Update ItineraryItems table structure
        logger.info("📋 Step 4: Updating ItineraryItems table structure...")
        if not update_itinerary_items_table():
            logger.error("❌ Failed to update ItineraryItems table")
            return False
        
        # Step 5: Migrate existing data
        logger.info("📋 Step 5: Migrating existing data...")
        if not migrate_existing_data():
            logger.error("❌ Failed to migrate existing data")
            return False
        
        # Step 6: Clean up
        logger.info("📋 Step 6: Cleaning up...")
        cleanup_backup()
        
        logger.info("🎉 Migration completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False

if __name__ == "__main__":
    success = run_migration()
    if success:
        print("\n✅ Migration completed successfully!")
        print("📝 New structure:")
        print("   - Itineraries table: Stores itinerary metadata")
        print("   - ItineraryItems table: Stores individual attraction visits")
        print("   - All existing data has been preserved and migrated")
        print("📁 Files structure:")
        print("   - src/models/itinerary.py: Contains Itinerary class")
        print("   - src/models/itinerary_item.py: Contains ItineraryItem class")
    else:
        print("\n❌ Migration failed! Check logs above for details.")
        sys.exit(1) 