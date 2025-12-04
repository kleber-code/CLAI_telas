from app.models import Notification, User
from peewee import DoesNotExist
import datetime

def create_notification(recipient_id, message, link=None):
    """
    Creates a new notification for a given user.
    """
    try:
        recipient = User.get(User.id == recipient_id)
        Notification.create(
            recipient=recipient,
            message=message,
            link=link,
            timestamp=datetime.datetime.now()
        )
        return True
    except DoesNotExist:
        print(f"Error: Recipient with ID {recipient_id} not found.")
        return False
    except Exception as e:
        print(f"Error creating notification: {e}")
        return False

def get_unread_notifications(user_id):
    """
    Fetches all unread notifications for a specific user.
    """
    try:
        return Notification.select().where(
            (Notification.recipient == user_id) & (Notification.is_read == False)
        ).order_by(Notification.timestamp.desc())
    except Exception as e:
        print(f"Error fetching unread notifications for user {user_id}: {e}")
        return []

def get_all_notifications(user_id):
    """
    Fetches all notifications for a specific user.
    """
    try:
        return Notification.select().where(
            Notification.recipient == user_id
        ).order_by(Notification.timestamp.desc())
    except Exception as e:
        print(f"Error fetching all notifications for user {user_id}: {e}")
        return []

def mark_notification_as_read(notification_id):
    """
    Marks a specific notification as read.
    """
    try:
        notification = Notification.get(Notification.id == notification_id)
        notification.is_read = True
        notification.save()
        return True
    except DoesNotExist:
        print(f"Error: Notification with ID {notification_id} not found.")
        return False
    except Exception as e:
        print(f"Error marking notification {notification_id} as read: {e}")
        return False

def mark_all_notifications_as_read(user_id):
    """
    Marks all notifications for a specific user as read.
    """
    try:
        notifications = Notification.select().where(
            (Notification.recipient == user_id) & (Notification.is_read == False)
        )
        for notification in notifications:
            notification.is_read = True
            notification.save()
        return True
    except Exception as e:
        print(f"Error marking all notifications for user {user_id} as read: {e}")
        return False
