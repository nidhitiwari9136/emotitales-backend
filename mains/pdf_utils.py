import pdfplumber
import re


def clean_text(text):
    """
    Cleans extracted text from PDF or TXT files.
    Removes encoding artifacts, extra spaces, and control characters.
    """

    if not text:
        return ""

    # Remove PDF encoding artifacts like (cid:123)
    text = re.sub(r"\(cid:\d+\)", "", text)

    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)

    # Remove non-printable characters
    text = "".join(ch for ch in text if ch.isprintable() or ch in "\n\t")

    return text.strip()


def extract_text_from_pdf(file):
    """
    Extract text from PDF using pdfplumber.
    Works with large PDFs (100+ pages).
    """

    file.seek(0)

    extracted = []

    try:
        with pdfplumber.open(file) as pdf:

            total_pages = len(pdf.pages)
            print("📄 PDF pages:", total_pages)

            for i, page in enumerate(pdf.pages):

                page_text = page.extract_text()

                if page_text:
                    extracted.append(page_text)

                # Progress log
                if (i + 1) % 10 == 0:
                    print(f"✅ Processed pages: {i + 1}/{total_pages}")

        full_text = "\n".join(extracted)

        return clean_text(full_text)

    except Exception as e:
        print("❌ PDF extraction error:", str(e))
        return ""


def extract_text_from_txt(file):
    """
    Extract text from TXT file.
    """

    try:
        file.seek(0)

        content = file.read().decode("utf-8", errors="ignore")

        return clean_text(content)

    except Exception as e:
        print("❌ TXT extraction error:", str(e))
        return ""