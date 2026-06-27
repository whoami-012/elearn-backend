# Import all models here so that Base.metadata is populated
# before init_db() calls Base.metadata.create_all()

from app.models.user import User
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.models.payment import Payment
from app.models.lesson import Lesson
from app.models.exam import Exam
from app.models.question import Question
from app.models.attempt import Attempt
from app.models.note import Note
from app.models.live_class import LiveClass, LiveClassAttendance
from app.messaging.models import (
    ConversationReadState,
    DirectConversation,
    Message,
    MessageAttachment,
)

__all__ = [
    "User",
    "Course",
    "Enrollment",
    "Payment",
    "Lesson",
    "Exam",
    "Question",
    "Attempt",
    "Note",
    "LiveClass",
    "LiveClassAttendance",
    "DirectConversation",
    "Message",
    "MessageAttachment",
    "ConversationReadState",
]
