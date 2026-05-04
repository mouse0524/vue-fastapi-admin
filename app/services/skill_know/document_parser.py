from pathlib import Path


class SkillKnowDocumentParser:
    async def parse(self, file_path: str, file_type: str) -> str:
        ext = (file_type or Path(file_path).suffix).lower().lstrip(".")
        if ext in {"txt", "md", "markdown"}:
            return Path(file_path).read_text(encoding="utf-8", errors="ignore")
        if ext == "pdf":
            return self._parse_pdf(file_path)
        if ext in {"docx", "doc"}:
            return self._parse_docx(file_path)
        return Path(file_path).read_text(encoding="utf-8", errors="ignore")

    def _parse_pdf(self, file_path: str) -> str:
        try:
            from pypdf import PdfReader

            reader = PdfReader(file_path)
            return "\n\n".join(page.extract_text() or "" for page in reader.pages).strip()
        except Exception as exc:
            raise ValueError(f"PDF 解析失败: {exc}") from exc

    def _parse_docx(self, file_path: str) -> str:
        try:
            from docx import Document

            doc = Document(file_path)
            return "\n".join(p.text for p in doc.paragraphs if p.text).strip()
        except Exception as exc:
            raise ValueError(f"Word 解析失败: {exc}") from exc


skill_know_document_parser = SkillKnowDocumentParser()
