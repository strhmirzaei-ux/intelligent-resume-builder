from typing import List, Dict, Any

from app.schemas.resume import ResumeSchema

class GapAnalyzer:
    """
    تحلیل‌گر شکاف اطلاعاتی رزومه.
    بررسی انطباق خروجی با ورودی، شناسایی نواقص و محاسبه امتیاز پوشش.
    """

    def __init__(self, resume: ResumeSchema | None = None, original_text: str = ""):
        self.resume = resume
        self.original_text = original_text
        self.deficiencies = []

    # --- ۱. مقایسه با متن اصلی (ضد جعل) ---
    def check_hallucination(self) -> List[str]:
        """
        اگر کلمه‌ای در داده‌های حساس (مثل نام شرکت یا دانشگاه) باشد که در متن اصلی نیست،
        آن را به عنوان 'احتمال جعل' علامت می‌زند.
        """
        hallucinated_facts = []
        
        # بررسی فیلدهای حساس (مثال: سوابق کاری و تحصیلات)
        if self.resume is None:
            return ["رزومه‌ای برای تحلیل ارائه نشده است."]
        source = self.original_text.casefold()
        for job in self.resume.work_experiences:
            if job.company_name and job.company_name.casefold() not in source:
                hallucinated_facts.append(
                    f"شرکت '{job.company_name}' در متن ورودی یافت نشد."
                )
        
        for edu in self.resume.educations:
            if edu.institution_name and edu.institution_name.casefold() not in source:
                hallucinated_facts.append(
                    f"مؤسسه '{edu.institution_name}' در متن ورودی یافت نشد."
                )
        
        self.deficiencies.extend(hallucinated_facts)
        return hallucinated_facts

    # --- ۲. شناسایی فیلدهای خالی یا ناقص ---
    def identify_missing_fields(self) -> List[str]:
        """
        شناسایی فیلدهایی که یا خالی هستند یا اطلاعات حیاتی مثل تاریخ ندارند.
        """
        missing = []
        
        # اطلاعات فردی
        if self.resume is None:
            return ["رزومه‌ای برای تحلیل ارائه نشده است."]
        if not self.resume.personal_info.first_name or not self.resume.personal_info.last_name:
            missing.append("اطلاعات نام و نام‌خانوادگی ناقص است.")
        
        # سوابق کاری بدون تاریخ
        for i, job in enumerate(self.resume.work_experiences):
            if not job.start_date:
                missing.append(
                    f"تاریخ شروع برای سابقه کاری '{job.job_title or 'بدون عنوان'}' "
                    f"در '{job.company_name or 'بدون شرکت'}' ثبت نشده است."
                )
            if not job.description or len(job.description) < 10:
                missing.append(
                    f"توضیحات سابقه کاری '{job.job_title or 'بدون عنوان'}' "
                    "بسیار کوتاه یا خالی است."
                )

        # مهارت‌های بدون سطح تسلط
        for skill in self.resume.skills:
            if not skill.level:
                missing.append(f"سطح تسلط برای مهارت '{skill.name}' مشخص نیست.")

        self.deficiencies.extend(missing)
        return missing

    # --- ۳. محاسبه امتیاز پوشش (Coverage Score) ---
    def calculate_coverage_score(self) -> float:
        """
        محاسبه درصد تکمیل رزومه بر اساس وزن فیلدها.
        وزن‌ها: اطلاعات فردی (20%)، سوابق (40%)، تحصیلات (20%)، مهارت‌ها (20%)
        """
        if self.resume is None:
            return 0.0
        score = 0.0
        
        # وزن اطلاعات فردی
        if self.resume.personal_info.first_name and self.resume.personal_info.last_name:
            score += 20
            
        # وزن سوابق کاری (حداقل یک سابقه کامل)
        if self.resume.work_experiences:
            valid_jobs = [
                j for j in self.resume.work_experiences
                if j.company_name and j.job_title and j.start_date
            ]
            if valid_jobs:
                score += 40
        
        # وزن تحصیلات
        if self.resume.educations:
            score += 20
            
        # وزن مهارت‌ها
        if self.resume.skills:
            score += 20
            
        return score

    # --- ۴. خروجی نهایی تحلیل ---
    def run_analysis(self) -> Dict[str, Any]:
        """اجرای کامل تحلیل و بازگرداندن گزارش نهایی."""
        self.deficiencies = [] # Reset
        
        hallucinations = self.check_hallucination()
        missing = self.identify_missing_fields()
        score = self.calculate_coverage_score()
        
        return {
            "coverage_score": score,
            "is_valid": len(hallucinations) == 0,
            "deficiencies": self.deficiencies,
            "suggestions": self._generate_suggestions()
        }

    def analyze(
        self,
        resume: ResumeSchema | dict | None = None,
        original_text: str | None = None,
    ) -> Dict[str, Any]:
        if resume is not None:
            self.resume = (
                resume if isinstance(resume, ResumeSchema)
                else ResumeSchema.model_validate(resume)
            )
        if original_text is not None:
            self.original_text = original_text
        return self.run_analysis()

    def _generate_suggestions(self) -> List[str]:
        """تبدیل نواقص به پیشنهادات کاربردی برای کاربر."""
        suggestions = []
        for d in self.deficiencies:
            suggestions.append(f"لطفاً این مورد را اصلاح یا تکمیل کنید: {d}")
        return suggestions
