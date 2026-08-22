# app/services/resume_service.py
from app.schemas.resume import ResumeSchema


class ResumeService:
    @staticmethod
    def create_empty_resume() -> ResumeSchema:
        """یک نمونه رزومه خالی با مقادیر پیش‌فرض می‌سازد."""
        return ResumeSchema()

    @staticmethod
    def map_raw_to_schema(raw_data: dict) -> ResumeSchema:
        """داده‌های خام را به Schema معتبر تبدیل می‌کند."""
        # در آینده اینجا منطق هوش مصنوعی برای پر کردن فیلدها اضافه می‌شود
        # فعلاً فقط Validate می‌کند
        return ResumeSchema(**raw_data)
