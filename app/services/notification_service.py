class NotificationService:
    """FCM-ready boundary. Current deployment has no notification transport."""

    async def publish(self, event: str, live_class_id, course_id) -> None:
        return None


notification_service = NotificationService()
