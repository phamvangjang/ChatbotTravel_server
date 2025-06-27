from src import create_app
from src.services.scheduler_service import start_itinerary_reminder_scheduler

app = create_app()

if __name__ == '__main__':
    # Start itinerary reminder scheduler
    start_itinerary_reminder_scheduler()
    app.run(debug=True) 