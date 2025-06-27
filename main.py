from src import create_app
from src.services.scheduler_service import start_notification_scheduler

app = create_app()

if __name__ == '__main__':
    # Start notification scheduler
    start_notification_scheduler()
    app.run(debug=True) 