import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.services.data_crawler import crawler

def main():
    app = create_app()
    with app.app_context():
        print("Bắt đầu crawl dữ liệu từ VNExpress...")
        crawler.update_database()
        print("Hoàn thành!")

if __name__ == "__main__":
    main() 