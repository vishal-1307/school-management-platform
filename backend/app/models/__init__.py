"""Models package — import all ORM models so Alembic and Base.metadata see them."""

from app.models.academic import AcademicYear, Class, Section, Subject  # noqa: F401
from app.models.admission import AdmissionEnquiry  # noqa: F401
from app.models.audit import AuditLog  # noqa: F401
from app.models.attendance import Attendance, AttendanceStatus, StaffAttendance  # noqa: F401
from app.models.cms import Achievement, GalleryAlbum, GalleryImage, NewsEvent  # noqa: F401
from app.models.communication import DeliveryStatus, WhatsAppMessageLog  # noqa: F401
from app.models.contact import ContactMessage  # noqa: F401
from app.models.exam import Exam, ExamSubject, Mark  # noqa: F401
from app.models.fee import FeeStructure, FeeTransaction, PaymentMode  # noqa: F401
from app.models.homework import Homework, HomeworkSubmission, SubmissionStatus  # noqa: F401
from app.models.notice import Notice, NoticeAudience  # noqa: F401
from app.models.school import School  # noqa: F401
from app.models.staff import Staff, StaffSubjectAssignment  # noqa: F401
from app.models.student import Parent, Student  # noqa: F401
from app.models.timetable import TimetableSlot  # noqa: F401
from app.models.user import User, UserRole  # noqa: F401
