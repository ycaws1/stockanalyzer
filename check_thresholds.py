
import os
import sys
from dotenv import load_dotenv

# Add the parent directory to sys.path to import app
sys.path.append(os.getcwd())
load_dotenv('backend/.env')

from backend.app.services.push_notifications import PushNotificationService

print("Current Thresholds:")
print(PushNotificationService.get_thresholds())
print("VAPID_PUBLIC_KEY:", os.getenv('VAPID_PUBLIC_KEY')[:10] + "...")
print("ALERT_THRESHOLD_1D:", os.getenv('ALERT_THRESHOLD_1D'))
