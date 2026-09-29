from __future__ import annotations

from typing import Any
from uuid import uuid4

from app.core.config import get_settings
from app.integrations.embedding_service import EmbeddingService
from app.modules.conversation.unified_agent import UnifiedResumeAgent
from app.modules.extraction.llm_extractor import ResumeLLMExtractor
from app.modules.gap_analysis.analyzer import GapAnalyzer
from app.modules.preprocessing.normalizer import PersianTextNormalizer
from app.modules.question_generation.generator import QuestionGenerator
from app.schemas.resume import ResumeSchema
from app.services.entity_resolution import EntityResolver
from app.storage.json_store import JsonStore


class ResumePipelineService:
    MAX_SESSION_QUESTIONS = 8

    def __init__(
        self,
        extractor: ResumeLLMExtractor,
        store: JsonStore,
        normalizer: PersianTextNormalizer | None = None,
        question_generator: QuestionGenerator | None = None,
        embedding_service: EmbeddingService | None = None,
        entity_resolver: EntityResolver | None = None,
        unified_agent: UnifiedResumeAgent | None = None,
    ) -> None:
        self.extractor = extractor
        self.store = store
        self.normalizer = normalizer or PersianTextNormalizer()
        self.questions = question_generator or QuestionGenerator(
            llm=getattr(extractor, "llm", None)
        )
        self.unified_agent = unified_agent or (
            UnifiedResumeAgent(llm=getattr(extractor, "llm", None))
            if question_generator is None and getattr(extractor, "llm", None) is not None
            else None
        )
        self.settings = get_settings()
        self.embedding_service = embedding_service or EmbeddingService()
        self.entity_resolver = entity_resolver or EntityResolver(
            self.embedding_service,
            threshold=self.settings.entity_resolution_threshold,
        )

    def process(self, text: str, resume_id: str | None = None) -> dict[str, Any]:
        normalized = self.normalizer.clean_text(text)
        previous = (
            self.store.get(resume_id, max_age_seconds=self.settings.session_ttl_seconds)
            if resume_id
            else None
        )
        if self.unified_agent is not None:
            return self._process_unified(text, normalized, resume_id, previous)

        resume = self.extractor.extract(normalized)
        if previous:
            old_resume = ResumeSchema.model_validate(previous["resume"])
            merged_resume = self.merge_with_entity_resolution(
                old_resume.model_dump(mode="json"),
                resume.model_dump(mode="json"),
            )
            resume = ResumeSchema.model_validate(merged_resume)
            resume = self._apply_answer_fallback(resume, previous, normalized)
        conversation_text = normalized
        if previous:
            previous_messages = previous.get("messages", [])
            conversation_text = "\n".join(
                [
                    str(message.get("content", ""))
                    for message in previous_messages
                    if message.get("role") == "user"
                ]
                + [normalized]
            )
        analysis = GapAnalyzer(resume, conversation_text).run_analysis()
        if previous:
            previous_score = float(previous.get("analysis", {}).get("coverage_score", 0))
            if analysis["coverage_score"] < previous_score:
                analysis["coverage_score"] = previous_score
                graph = analysis.get("graph")
                if isinstance(graph, dict):
                    graph["weighted_score"] = previous_score
        resume_id = resume_id or str(uuid4())
        previously_asked = list(previous.get("asked_deficiencies", [])) if previous else []
        deficiency_codes = list(analysis.get("deficiency_codes", []))
        previous_codes = list(previous.get("asked_deficiency_codes", [])) if previous else []
        if previous and not previous_codes:
            previous_codes = self._infer_asked_codes(previous.get("next_question"))
        if previous and not previous_codes:
            previous_codes = self._codes_for_previous_question(
                previous.get("next_question"),
                analysis.get("deficiencies", []),
                deficiency_codes,
            )
        question_history = self._load_question_history(previous)
        if previous:
            self._update_question_answers(question_history, previous, analysis, normalized)
        blocked_codes = set(previous_codes)
        blocked_codes.update(
            str(item["question_code"])
            for item in question_history
            if item.get("question_code") and not item.get("answered", False)
        )
        llm_deficiencies = {
            deficiency
            for index, deficiency in enumerate(analysis.get("deficiencies", []))
            if index >= len(deficiency_codes) or deficiency_codes[index] not in blocked_codes
        }
        question_kwargs = {
            "resume_context": resume.model_dump(mode="json"),
            "previous_questions": [
                str(item.get("question_text") or item.get("text"))
                for item in question_history
                if item.get("question_text") or item.get("text")
            ],
            "conversation_context": conversation_text,
            "llm_deficiencies": llm_deficiencies,
            "llm_question_limit": 1,
        }
        generated_questions = (
            self.questions.generate(analysis.get("deficiencies", []), **question_kwargs)
            if len(question_history) < self.MAX_SESSION_QUESTIONS
            else []
        )
        next_question = self._select_question(
            generated_questions,
            deficiency_codes,
            analysis.get("deficiencies", []),
            question_history,
            blocked_codes=blocked_codes,
        )
        next_question_code = (
            self._question_code(next_question, deficiency_codes, analysis.get("deficiencies", []))
            if next_question
            else None
        )
        if next_question:
            question_history.append(
                self._question_record(next_question, next_question_code)
            )
        asked_deficiencies = previously_asked + (
            [next_question["source_deficiency"]] if next_question else []
        )
        asked_deficiency_codes = previous_codes + (
            [next_question_code]
            if next_question and next_question_code
            else []
        )
        messages = list(previous.get("messages", [])) if previous else []
        messages.append({"role": "user", "content": text})
        if next_question:
            messages.append({"role": "assistant", "content": next_question["text"]})

        record = {
            "resume_id": resume_id,
            "raw_text": text,
            "normalized_text": normalized,
            "resume": resume.model_dump(mode="json"),
            "analysis": analysis,
            "asked_deficiencies": asked_deficiencies,
            "asked_deficiency_codes": asked_deficiency_codes,
            "questions": question_history,
            "next_question": next_question["text"] if next_question else None,
            "messages": messages,
        }
        self.store.put(resume_id, record)
        return record

    def _process_unified(
        self,
        raw_text: str,
        normalized: str,
        resume_id: str | None,
        previous: dict[str, Any] | None,
    ) -> dict[str, Any]:
        resume_id = resume_id or str(uuid4())
        current_resume = previous.get("resume", {}) if previous else ResumeSchema().model_dump(mode="json")
        if previous:
            current_resume = UnifiedResumeAgent._normalize_resume_payload(
                UnifiedResumeAgent._unwrap_payload(current_resume)
            )
        previous_questions = self._load_question_history(previous)
        prior_analysis = previous.get("analysis", {}) if previous else {}
        suppressed_facts = list(previous.get("suppressed_facts", [])) if previous else []
        recent_messages = (previous.get("messages", []) if previous else [])[-8:]
        result = self.unified_agent.invoke(
            user_message=normalized,
            current_resume=current_resume,
            conversation_summary=str(previous.get("conversation_summary", "")) if previous else "",
            recent_messages=recent_messages,
            previous_questions=previous_questions,
            deficiencies=list(prior_analysis.get("deficiencies", [])),
            suppressed_facts=suppressed_facts,
        )

        base = ResumeSchema.model_validate(current_resume).model_dump(mode="json")
        extracted = result.extracted_resume
        if extracted:
            merged = self.merge_with_entity_resolution(base, extracted)
            if extracted.get("professional_summary"):
                merged["professional_summary"] = extracted["professional_summary"]
        else:
            merged = base
        merged = self._apply_operations(merged, result.operations)
        resume = ResumeSchema.model_validate(merged)
        resume = self._apply_answer_fallback(resume, previous or {}, normalized)

        conversation_text = self._conversation_context(previous, normalized)
        analysis = GapAnalyzer(resume, conversation_text).run_analysis()
        previous_score = float(prior_analysis.get("coverage_score", 0))
        if analysis["coverage_score"] < previous_score:
            analysis["coverage_score"] = previous_score
            if isinstance(analysis.get("graph"), dict):
                analysis["graph"]["weighted_score"] = previous_score

        history = previous_questions
        if previous:
            self._update_question_answers(history, previous, analysis, normalized)
        deficiency_codes = list(analysis.get("deficiency_codes", []))
        previous_codes = list(previous.get("asked_deficiency_codes", [])) if previous else []
        if previous and not previous_codes:
            previous_codes = self._infer_asked_codes(previous.get("next_question"))
        blocked_codes = set(previous_codes)
        blocked_codes.update(
            str(item["question_code"])
            for item in history
            if item.get("question_code") and not item.get("answered", False)
        )
        candidate = None
        if result.next_question and len(history) < self.MAX_SESSION_QUESTIONS:
            candidate = {
                "text": result.next_question,
                "source_deficiency": self._first_unblocked_deficiency(
                    analysis.get("deficiencies", []), deficiency_codes, blocked_codes
                ),
            }
            candidate = self._select_question(
                [candidate], deficiency_codes, analysis.get("deficiencies", []), history, blocked_codes
            )
        next_code = self._question_code(candidate, deficiency_codes, analysis.get("deficiencies", [])) if candidate else None
        if candidate:
            history.append(self._question_record(candidate, next_code))

        messages = list(previous.get("messages", [])) if previous else []
        messages.append({"role": "user", "content": raw_text})
        if candidate:
            messages.append({"role": "assistant", "content": candidate["text"]})
        record = {
            "resume_id": resume_id,
            "raw_text": raw_text,
            "normalized_text": normalized,
            "resume": resume.model_dump(mode="json"),
            "analysis": analysis,
            "asked_deficiencies": (list(previous.get("asked_deficiencies", [])) if previous else [])
            + ([candidate["source_deficiency"]] if candidate and candidate.get("source_deficiency") else []),
            "asked_deficiency_codes": previous_codes + ([next_code] if next_code else []),
            "questions": history,
            "next_question": candidate["text"] if candidate else None,
            "messages": messages,
            "conversation_summary": result.memory_summary or (previous.get("conversation_summary", "") if previous else ""),
            "suppressed_facts": suppressed_facts + [
                str(operation.get("path"))
                for operation in result.operations
                if str(operation.get("op", "")).lower() == "remove" and operation.get("path")
            ],
            "operation_history": list(previous.get("operation_history", [])) if previous else [],
        }
        record["operation_history"].extend(result.operations)
        self.store.put(resume_id, record)
        return record

    @staticmethod
    def _conversation_context(previous: dict[str, Any] | None, normalized: str) -> str:
        old = previous.get("messages", []) if previous else []
        return "\n".join([str(item.get("content", "")) for item in old if item.get("role") == "user"] + [normalized])

    @staticmethod
    def _first_unblocked_deficiency(deficiencies: list[str], codes: list[str], blocked: set[str]) -> str | None:
        for index, deficiency in enumerate(deficiencies):
            if index >= len(codes) or codes[index] not in blocked:
                return deficiency
        return None

    @staticmethod
    def _apply_operations(resume: dict[str, Any], operations: list[dict[str, Any]]) -> dict[str, Any]:
        import copy

        result = copy.deepcopy(resume)
        for operation in operations:
            op = str(operation.get("op", "")).lower()
            path = operation.get("path")
            if not isinstance(path, str) or not path.startswith("/"):
                continue
            parts = [part.replace("~1", "/").replace("~0", "~") for part in path[1:].split("/") if part]
            if not parts:
                continue
            parent: Any = result
            try:
                for part in parts[:-1]:
                    parent = parent[int(part)] if isinstance(parent, list) else parent[part]
                key = parts[-1]
                if op in {"add", "replace", "merge"}:
                    value = operation.get("value")
                    if op == "merge" and isinstance(parent, dict) and isinstance(parent.get(key), dict) and isinstance(value, dict):
                        parent[key] = {**parent[key], **value}
                    elif isinstance(parent, list) and key == "-":
                        parent.append(value)
                    elif isinstance(parent, list):
                        index = int(key)
                        if op == "add":
                            parent.insert(index, value)
                        else:
                            parent[index] = value
                    else:
                        parent[key] = value
                elif op == "remove":
                    if isinstance(parent, list):
                        parent.pop(int(key))
                    else:
                        parent.pop(key, None)
            except (KeyError, IndexError, TypeError, ValueError):
                continue
        return result

    def _load_question_history(self, previous: dict[str, Any] | None) -> list[dict[str, Any]]:
        if not previous:
            return []
        history = [dict(item) for item in previous.get("questions", []) if isinstance(item, dict)]
        legacy_text = previous.get("next_question")
        if legacy_text and not any(
            item.get("question_text") == legacy_text or item.get("text") == legacy_text
            for item in history
        ):
            legacy_codes = list(previous.get("asked_deficiency_codes", []))
            code = legacy_codes[-1] if legacy_codes else self._infer_asked_codes(legacy_text)[0:1]
            history.append(
                {
                    "text": legacy_text,
                    "question_text": legacy_text,
                    "question_code": code[0] if isinstance(code, list) and code else code,
                    "embedding": self.embedding_service.embed(str(legacy_text)),
                    "answered": False,
                }
            )
        return history

    def _update_question_answers(
        self,
        history: list[dict[str, Any]],
        previous: dict[str, Any],
        analysis: dict[str, Any],
        answer: str,
    ) -> None:
        current_codes = set(analysis.get("deficiency_codes", []))
        previous_question = previous.get("next_question")
        for item in history:
            if item.get("answered"):
                continue
            code = item.get("question_code")
            if code and code not in current_codes:
                item["answered"] = True
                continue
            if previous_question and item.get("question_text") == previous_question:
                item["answered"] = self._is_related_answer(
                    str(item.get("question_text", "")), answer
                )

    def _select_question(
        self,
        candidates: list[dict[str, Any]],
        deficiency_codes: list[str],
        deficiencies: list[str],
        history: list[dict[str, Any]],
        blocked_codes: set[str],
    ) -> dict[str, Any] | None:
        for candidate in candidates:
            code = self._question_code(candidate, deficiency_codes, deficiencies)
            if code in blocked_codes:
                continue
            if self._is_duplicate_question(candidate["text"], code, history):
                continue
            return candidate
        return None

    def _is_duplicate_question(
        self, text: str, code: str | None, history: list[dict[str, Any]]
    ) -> bool:
        current_embedding = self.embedding_service.embed(text)
        normalized = self._normalize_question(text)
        for item in history:
            old_text = str(item.get("question_text") or item.get("text") or "")
            if not old_text:
                continue
            if normalized == self._normalize_question(old_text):
                return True
            old_embedding = item.get("embedding")
            if old_embedding is None:
                old_embedding = self.embedding_service.embed(old_text)
            similarity = self.embedding_service.cosine_similarity(current_embedding, old_embedding)
            if similarity is not None and similarity >= self.settings.question_similarity_threshold:
                return True
            if code and item.get("question_code") == code and not item.get("answered", False):
                return True
        return False

    def _is_related_answer(self, question: str, answer: str) -> bool:
        similarity = self.embedding_service.cosine_similarity(
            self.embedding_service.embed(question), self.embedding_service.embed(answer)
        )
        return (
            similarity is not None
            and similarity >= self.settings.question_answer_similarity_threshold
        )

    def _question_record(self, question: dict[str, Any], code: str | None) -> dict[str, Any]:
        text = str(question["text"])
        return {
            "text": text,
            "question_text": text,
            "question_code": code,
            "embedding": self.embedding_service.embed(text),
            "answered": False,
        }

    @staticmethod
    def _question_code(
        question: dict[str, Any] | None,
        codes: list[str],
        deficiencies: list[str],
    ) -> str | None:
        if not question:
            return None
        source = question.get("source_deficiency")
        if source in deficiencies:
            index = deficiencies.index(source)
            if index < len(codes):
                return codes[index]
        return source

    @staticmethod
    def _normalize_question(text: str) -> str:
        return " ".join(text.casefold().split())

    def merge_with_entity_resolution(self, old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
        """Merge extracted data while resolving work entities semantically."""
        merged = dict(old)
        for key, value in new.items():
            if value is None or value == "" or value == []:
                continue
            if key in {"work_experiences", "internships"} and isinstance(value, list):
                if key == "work_experiences":
                    merged[key] = self._merge_work_experiences_with_resolution(
                        merged.get(key, []), value
                    )
                else:
                    merged[key] = self._merge_experience_lists(merged.get(key, []), value)
            elif isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = self.merge_with_entity_resolution(merged[key], value)
            elif isinstance(value, list) and isinstance(merged.get(key), list):
                merged[key] = self._merge_accumulated_list(merged[key], value)
            elif key == "status":
                if value not in (None, "unverified"):
                    merged[key] = value
            elif key == "confidence":
                if value is not None:
                    merged[key] = value
            elif merged.get(key) not in (None, "", []):
                # Treat each user turn as an addition to the resume. The model
                # may omit or reinterpret earlier facts, so keep populated facts.
                continue
            else:
                merged[key] = value
        return merged

    @staticmethod
    def _merge_accumulated_list(old: list[Any], new: list[Any]) -> list[Any]:
        result = list(old)
        for incoming in new:
            if isinstance(incoming, dict):
                identity_keys = ("name", "institution_name", "degree", "role", "url")
                identity = next(
                    (incoming.get(key) for key in identity_keys if incoming.get(key)), None
                )
                match = next(
                    (
                        index
                        for index, existing in enumerate(result)
                        if isinstance(existing, dict)
                        and identity
                        and any(existing.get(key) == identity for key in identity_keys)
                    ),
                    None,
                )
                if match is None:
                    if incoming not in result:
                        result.append(incoming)
                else:
                    result[match] = ResumePipelineService.merge(result[match], incoming)
            elif incoming not in result:
                result.append(incoming)
        return result

    def _merge_work_experiences_with_resolution(
        self, old: list[Any], new: list[Any]
    ) -> list[Any]:
        result = [dict(item) for item in old if isinstance(item, dict)]
        for incoming in new:
            if not isinstance(incoming, dict):
                continue
            match = self.entity_resolver.find_work_experience_match(result, incoming)
            if match.index is None:
                result.append(dict(incoming))
            else:
                existing = result[match.index]
                merged = self.merge(existing, incoming)
                # Keep the established identity when a semantic alias matched
                # an existing entity. Missing identity fields may still be
                # filled by the incoming extraction.
                if existing.get("company_name") and incoming.get("company_name"):
                    merged["company_name"] = existing["company_name"]
                if existing.get("job_title") and incoming.get("job_title"):
                    merged["job_title"] = existing["job_title"]
                result[match.index] = merged
        return result

    def get(self, resume_id: str) -> dict[str, Any] | None:
        return self.store.get(resume_id)

    @staticmethod
    def questions_for(record: dict[str, Any]) -> list[dict[str, Any]]:
        return QuestionGenerator().generate(record["analysis"].get("deficiencies", []))

    @staticmethod
    def merge(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
        merged = dict(old)
        for key, value in new.items():
            if value is None or value == "" or value == []:
                continue
            if key in {"work_experiences", "internships"} and isinstance(value, list):
                merged[key] = ResumePipelineService._merge_experience_lists(
                    merged.get(key, []), value
                )
            elif isinstance(value, list) and isinstance(merged.get(key), list):
                merged[key] = ResumePipelineService._merge_accumulated_list(merged[key], value)
            elif isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = ResumePipelineService.merge(merged[key], value)
            elif key == "status":
                if value not in (None, "unverified"):
                    merged[key] = value
            elif key == "confidence":
                if value is not None:
                    merged[key] = value
            elif merged.get(key) not in (None, "", []):
                continue
            else:
                merged[key] = value
        return merged

    @staticmethod
    def _apply_answer_fallback(
        resume: ResumeSchema, previous: dict[str, Any], answer: str
    ) -> ResumeSchema:
        """Preserve a direct answer when extraction omits the asked detail."""
        question = str(previous.get("next_question") or "")
        answer = answer.strip()
        if not answer:
            return resume
        data = resume.model_dump(mode="json")

        if "زبان" in question and not data.get("languages"):
            data["languages"] = [{
                "name": answer[:100],
                "status": "confirmed",
                "confidence": 0.8,
                "evidence": [{"source_text": answer}],
            }]
            return ResumeSchema.model_validate(data)

        if any(term in question for term in ("وظایف", "مسئولیت", "دستاورد", "توضیحات")):
            work_items = data.get("work_experiences") or []
            if work_items:
                target = work_items[-1]
                if not target.get("description") and not target.get("key_responsibilities"):
                    target["description"] = answer
                    target["key_responsibilities"] = [answer]
                evidence = target.setdefault("evidence", [])
                if not any(item.get("source_text") == answer for item in evidence):
                    evidence.append({"source_text": answer})
                return ResumeSchema.model_validate(data)
        return resume

    @staticmethod
    def _merge_experience_lists(old: list[Any], new: list[Any]) -> list[Any]:
        result = [dict(item) for item in old if isinstance(item, dict)]
        for incoming in new:
            if not isinstance(incoming, dict):
                continue
            candidates = [
                index
                for index, existing in enumerate(result)
                if (
                    incoming.get("company_name")
                    and existing.get("company_name")
                    and incoming["company_name"].casefold()
                    == existing["company_name"].casefold()
                )
                or (
                    incoming.get("job_title")
                    and existing.get("job_title")
                    and incoming["job_title"].casefold()
                    == existing["job_title"].casefold()
                )
            ]
            index = candidates[0] if candidates else (len(result) - 1 if result else None)
            if index is None:
                result.append(dict(incoming))
            else:
                result[index] = ResumePipelineService.merge(result[index], incoming)
        return result

    @staticmethod
    def _infer_asked_codes(question: Any) -> list[str]:
        text = str(question or "")
        codes: list[str] = []
        if any(term in text for term in ("وظایف", "مسئولیت")):
            codes.append("work_experience.responsibilities")
        if "دستاورد" in text:
            codes.append("work_experience.achievements")
        if codes:
            return codes
        if any(term in text for term in ("نام شرکت", "عنوان شغلی")):
            return ["work_experience.experiences"]
        if any(term in text for term in ("مدت", "تاریخ شروع")):
            return ["work_experience.duration"]
        if "زبان" in text:
            return ["interactive_skills.languages"]
        return []

    @staticmethod
    def _codes_for_previous_question(
        question: Any, deficiencies: Any, codes: Any
    ) -> list[str]:
        question_text = str(question or "")
        for index, deficiency in enumerate(deficiencies or []):
            if (
                str(deficiency)
                and str(deficiency) in question_text
                and index < len(codes or [])
            ):
                return [codes[index]]
        return []
