from fastapi import APIRouter
from app.api.v1.endpoints import (
    auth,
    courses,
    upload,
    notes,
    enrollments,
    lessons,
    exams,
    attempts,
    payments,
    users,
    live_classes,
    messaging,
)

# Central v1 router — all endpoint routers are registered here
api_router = APIRouter()

api_router.include_router(auth.router)
api_router.include_router(courses.router)
api_router.include_router(lessons.router)
api_router.include_router(upload.router)
api_router.include_router(notes.router)
api_router.include_router(enrollments.router)
api_router.include_router(exams.router)
api_router.include_router(attempts.router)
api_router.include_router(payments.router)
api_router.include_router(users.router)
api_router.include_router(live_classes.router)
api_router.include_router(messaging.router)
