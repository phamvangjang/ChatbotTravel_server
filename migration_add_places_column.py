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

def update_database_charset():
    """Cập nhật charset của database và bảng Messages để hỗ trợ UTF-8"""
    
    app = create_app()
    
    with app.app_context():
        try:
            # Cập nhật charset của database
            db_charset_sql = text("""
            ALTER DATABASE CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """)
            
            db.session.execute(db_charset_sql)
            
            # Cập nhật charset của bảng Messages
            table_charset_sql = text("""
            ALTER TABLE Messages CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
            """)
            
            db.session.execute(table_charset_sql)
            
            # Cập nhật charset của cột places nếu tồn tại (bỏ qua JSON column vì không cần charset)
            try:
                # Kiểm tra xem cột places có tồn tại không
                check_sql = text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'Messages' AND COLUMN_NAME = 'places'
                """)
                result = db.session.execute(check_sql).fetchone()
                
                if result:
                    print("Note: JSON column 'places' does not need charset specification")
                else:
                    print("Note: Column 'places' does not exist yet")
            except Exception as e:
                print(f"Warning: Could not check places column: {e}")
            
            db.session.commit()
            
            print("Successfully updated database charset to utf8mb4")
            print("Successfully updated Messages table charset to utf8mb4")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error updating database charset: {str(e)}")

def add_places_column():
    """Thêm cột places vào bảng Messages"""
    
    app = create_app()
    
    with app.app_context():
        try:
            # Thêm cột places vào bảng Messages
            # JSON column không cần charset specification
            sql = text("""
            ALTER TABLE Messages 
            ADD COLUMN places JSON DEFAULT '[]'
            """)
            
            db.session.execute(sql)
            db.session.commit()
            
            print("Successfully added 'places' column to Messages table")
            print("Column type: JSON")
            print("Default value: '[]' (empty array)")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error adding places column: {str(e)}")
            
            # Kiểm tra xem cột đã tồn tại chưa
            try:
                check_sql = text("""
                SELECT COLUMN_NAME 
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = 'Messages' AND COLUMN_NAME = 'places'
                """)
                result = db.session.execute(check_sql).fetchone()
                
                if result:
                    print("Column 'places' already exists in Messages table")
                else:
                    print("Column 'places' does not exist and could not be created")
                    
            except Exception as check_error:
                print(f"Error checking column existence: {str(check_error)}")

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
            
            print("Successfully removed 'places' column from Messages table")
            
        except Exception as e:
            db.session.rollback()
            print(f"Error removing places column: {str(e)}")

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
                print("Column 'places' exists in Messages table:")
                print(f"   - Column name: {result[0]}")
                print(f"   - Data type: {result[1]}")
                print(f"   - Nullable: {result[2]}")
                print(f"   - Default: {result[3]}")
            else:
                print("Column 'places' does not exist in Messages table")
                
        except Exception as e:
            print(f"Error checking column: {str(e)}")

def check_database_charset():
    """Kiểm tra charset của database và bảng"""
    
    app = create_app()
    
    with app.app_context():
        try:
            # Kiểm tra charset của database
            db_charset_sql = text("""
            SELECT DEFAULT_CHARACTER_SET_NAME, DEFAULT_COLLATION_NAME
            FROM INFORMATION_SCHEMA.SCHEMATA 
            WHERE SCHEMA_NAME = DATABASE()
            """)
            
            db_result = db.session.execute(db_charset_sql).fetchone()
            
            if db_result:
                print("Database charset:")
                print(f"   - Character set: {db_result[0]}")
                print(f"   - Collation: {db_result[1]}")
            
            # Kiểm tra charset của bảng Messages
            table_charset_sql = text("""
            SELECT TABLE_COLLATION
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_NAME = 'Messages'
            """)
            
            table_result = db.session.execute(table_charset_sql).fetchone()
            
            if table_result:
                print("Messages table charset:")
                print(f"   - Collation: {table_result[0]}")
                
        except Exception as e:
            print(f"Error checking charset: {str(e)}")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Migration script for places column')
    parser.add_argument('action', choices=['add', 'remove', 'check', 'charset', 'update-charset'], 
                       help='Action to perform: add, remove, check, charset, or update-charset')
    
    args = parser.parse_args()
    
    if args.action == 'add':
        add_places_column()
    elif args.action == 'remove':
        rollback_places_column()
    elif args.action == 'check':
        check_places_column()
    elif args.action == 'charset':
        check_database_charset()
    elif args.action == 'update-charset':
        update_database_charset() 