import os
from config import MAX_CONTENT_LENGTH


def parse_document(filepath):
    """解析文档（.docx / .txt）"""
    file_ext = os.path.splitext(filepath)[1].lower()

    if file_ext == '.txt':
        content = _parse_txt(filepath)
    elif file_ext == '.docx':
        content = _parse_docx(filepath)
    else:
        raise ValueError(f"不支持的文件格式: {file_ext}，仅支持 .docx / .txt")

    if len(content) > MAX_CONTENT_LENGTH:
        content = content[:MAX_CONTENT_LENGTH]

    return content


def _parse_txt(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return f.read(MAX_CONTENT_LENGTH)


def _parse_docx(filepath):
    from docx import Document
    doc = Document(filepath)

    # 优先提取表格内容（分镜脚本通常是表格格式）
    tables_text = []
    for table in doc.tables:
        for row in table.rows:
            cells = [cell.text.strip() for cell in row.cells]
            tables_text.append(' | '.join(cells))

    if tables_text:
        return '\n'.join(tables_text)

    # 无表格则提取段落
    paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
    return '\n'.join(paragraphs[:500])
