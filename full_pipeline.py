import os
import re
import json
import pdfplumber

# ===============================
# PATH CONFIG (ABSOLUTE & SAFE)
# ===============================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)

RESULTS_JSON = os.path.join(OUTPUT_DIR, "results.json")
RESULTS_UPDATED_JSON = os.path.join(OUTPUT_DIR, "results_updated.json")

# ===============================
# REGEX
# ===============================
NUM_RE = re.compile(r"\d+(?:\.\d+)?")

# ===============================
# JSON HELPERS
# ===============================
def load_json(path):
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# ===============================
# DEBUG: PRINT FULL PDF TEXT
# ===============================
def debug_print_pdf_text(pdf_path):
    print("\n" + "=" * 100)
    print("🧾 FULL PDF TEXT (pdfplumber output)")
    print("=" * 100)

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            print(f"\n📄 PAGE {i + 1}")
            print("-" * 100)
            text = page.extract_text()
            print(text if text else "⚠️ NO TEXT FOUND")

    print("\n" + "=" * 100 + "\n")

# ===============================
# HEADER EXTRACTION
# ===============================
def extract_header(text):
    def gs(p):
        m = re.search(p, text, re.IGNORECASE)
        return m.group(1).strip() if m else None

    def gi(p):
        m = re.search(p, text, re.IGNORECASE)
        return int(m.group(1)) if m else None

    course_raw = gs(r"Course:\s*(.+)")
    if course_raw:
        course_raw = re.sub(r"\s*Offer\s*No\s*:\s*\d+", "", course_raw).strip()

    return {
        "program": gs(r"Program:\s*(.+)"),
        "teacher_name": gs(r"Teacher Name:\s*(.+)"),
        "course": course_raw,
        "total_students": gi(r"Total Student[s]?:\s*(\d+)"),
        "evaluation_count": gi(r"Evaluation Count:\s*(\d+)")
    }

# ===============================
# AVERAGE EXTRACTION (CORRECT)
# ===============================
def extract_averages_from_text(text):
    """
    Extract ONLY:
    - Learning Average
    - Attitude Average
    - Punctuality Average
    - Assessment Average

    Explicitly IGNORE:
    - Practical Average
    - Overall Average
    """

    averages = {}

    text = re.sub(r"\s+", " ", text)

    PATTERNS = {
        "learning": r"Learning\s*Average\s*:\s*((?:\d+(?:\.\d+)?\s*){5})",
        "attitude": r"Attitude\s*Average\s*:\s*((?:\d+(?:\.\d+)?\s*){5})",
        "punctuality": r"Punctuality\s*Average\s*:\s*((?:\d+(?:\.\d+)?\s*){5})",
        "assessment": r"Assessment\s*Average\s*:\s*((?:\d+(?:\.\d+)?\s*){5})",
    }

    for key, pattern in PATTERNS.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            nums = re.findall(r"\d+(?:\.\d+)?", match.group(1))
            if len(nums) == 5:
                averages[key] = nums

    return averages

def expand_averages(averages_dict):
    """
    Converts:
    averages.learning = [SA, A, U, D, SD]
    into:
    SA.averages.learning, A.averages.learning, ...
    """

    expanded = {}

    LABELS = ["SA", "A", "U", "D", "SD"]

    for category, values in averages_dict.items():
        if not isinstance(values, list) or len(values) != 5:
            continue

        for i, label in enumerate(LABELS):
            key = f"{label}.averages.{category}"
            expanded[key] = float(values[i])

    return expanded


# ===============================
# MAIN PIPELINE (SINGLE PDF)
# ===============================
def process_single_pdf(pdf_path, batch_code, semester, session):
    print("📄 Processing:", pdf_path)

    # 🔍 DEBUG PRINT
    debug_print_pdf_text(pdf_path)

    results = load_json(RESULTS_JSON)

    existing = {
        (r.get("source_pdf"), r.get("page"), r.get("course"))
        for r in results
    }

    pdf_name = os.path.basename(pdf_path)

    with pdfplumber.open(pdf_path) as pdf:
        for page_index, page in enumerate(pdf.pages):
            raw_text = page.extract_text() or ""

            header = extract_header(raw_text)
            averages = extract_averages_from_text(raw_text)
            expanded_averages = expand_averages(averages)

            key = (pdf_name, page_index + 1, header.get("course"))
            if key in existing:
                print("⏩ Skipping duplicate:", key)
                continue
            
            record = {
                "source_pdf": pdf_name,
                "page": page_index + 1,
                "batch_code": batch_code,
                "semester": semester,
                "session": session,
                **header,
                **expanded_averages
            }

            results.append(record)

    save_json(RESULTS_JSON, results)
    print(f"✅ results.json updated ({len(results)} total records)")

# ===============================
# CLEAN RESULTS
# ===============================
def clean_results_json():
    data = load_json(RESULTS_JSON)
    save_json(RESULTS_UPDATED_JSON, data)
    print("✅ results_updated.json created")
