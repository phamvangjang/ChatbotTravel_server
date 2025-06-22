#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Migration script để thêm cột places vào bảng Messages
Chạy script này để cập nhật database schema
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.models.base import db
from src import create_app
from sqlalchemy import text

def add_places_column():
    """Thêm cột places vào bảng Messages"""
    
    app = create_app()
    
    with app.app_context():
        try:
            # Thêm cột places vào bảng Messages
            # Sử dụng raw SQL vì SQLAlchemy có thể không hỗ trợ JSON column trong một số trường hợp
            sql = text("""
            ALTER TABLE Messages 
            ADD COLUMN places JSON DEFAULT '[]'
            """)
            
            db.session.execute(sql)
            db.session.commit()
            
            print("✅ Successfully added 'places' column to Messages table")
            print("✅ Column type: JSON")
            print("✅ Default value: '[]' (empty array)")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error adding places column: {str(e)}")
            
            # Kiểm tra xem cột đã tồn tại chưa
            try:
                check_sql = text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'Messages' AND COLUMN_NAME = 'places'
                """)
                result = db.session.execute(check_sql).fetchone()
                
                if result:
                    print("ℹ️  Column 'places' already exists in Messages table")
                else:
                    print("❌ Column 'places' does not exist and could not be created")
                    
            except Exception as check_error:
                print(f"❌ Error checking column existence: {str(check_error)}")

def rollback_places_column():
    """Xóa cột places khỏi bảng Messages (rollback)"""
    
    app = create_app()
    
    with app.app_context():
        try:
            # Xóa cột places khỏi bảng Messages
            sql = text("""
            ALTER TABLE Messages 
            DROP COLUMN places
            """)
            
            db.session.execute(sql)
            db.session.commit()
            
            print("✅ Successfully removed 'places' column from Messages table")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Error removing places column: {str(e)}")

def check_places_column():
    """Kiểm tra trạng thái cột places"""
    
    app = create_app()
    
    with app.app_context():
        try:
            # Kiểm tra xem cột places có tồn tại không
            sql = text("""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, COLUMN_DEFAULT
            FROM INFORMATION_SCHEMA.COLUMNS 
            WHERE TABLE_NAME = 'Messages' AND COLUMN_NAME = 'places'
            """)
            
            result = db.session.execute(sql).fetchone()
            
            if result:
                print("✅ Column 'places' exists in Messages table:")
                print(f"   - Column name: {result[0]}")
                print(f"   - Data type: {result[1]}")
                print(f"   - Nullable: {result[2]}")
                print(f"   - Default: {result[3]}")
            else:
                print("❌ Column 'places' does not exist in Messages table")
                
        except Exception as e:
            print(f"❌ Error checking column: {str(e)}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Migration script for places column')
    parser.add_argument('action', choices=['add', 'remove', 'check'], 
                       help='Action to perform: add, remove, or check places column')
    
    args = parser.parse_args()
    
    if args.action == 'add':
        add_places_column()
    elif args.action == 'remove':
        rollback_places_column()
    elif args.action == 'check':
        check_places_column() 