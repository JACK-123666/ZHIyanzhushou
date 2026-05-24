import os
from config import MAX_CONTENT_LENGTH


def parse_document(filepath):
    """解析文档，根据扩展名分发到对应解析器"""
    file_ext = os.path.splitext(filepath)[1].lower()

    content = _parse_by_extension(filepath, file_ext)

    if len(content) > MAX_CONTENT_LENGTH:
        content = content[:MAX_CONTENT_LENGTH]

    return content


def _parse_by_extension(filepath, file_ext):
    if file_ext == '.txt':
        return _parse_txt(filepath)
    elif file_ext == '.docx':
        return _parse_docx(filepath)
    elif file_ext == '.pdf':
        return _parse_pdf(filepath)
    elif file_ext == '.pptx':
        return _parse_pptx(filepath)
    else:
        raise ValueError(f"不支持的文件格式: {file_ext}")


def _parse_txt(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read(MAX_CONTENT_LENGTH)


def _parse_docx(filepath):
    from docx import Document
    doc = Document(filepath)
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    max_paragraphs = 500
    if len(paragraphs) > max_paragraphs:
        paragraphs = paragraphs[:max_paragraphs]
    return '\n'.join(paragraphs)


def _parse_pdf(filepath):
    import pypdf
    with open(filepath, 'rb') as f:
        reader = pypdf.PdfReader(f)
        max_pages = min(len(reader.pages), 50)
        pages = reader.pages[:max_pages]
        return '\n'.join([page.extract_text() or '' for page in pages])


def _parse_pptx(filepath):
    from pptx import Presentation
    presentation = Presentation(filepath)
    slides_text = []
    max_slides = min(len(presentation.slides), 50)
    slides = list(presentation.slides)[:max_slides]
    for slide in slides:
        for shape in slide.shapes:
            if hasattr(shape, 'text') and shape.text.strip():
                slides_text.append(shape.text.strip())
    return '\n'.join(slides_text)
