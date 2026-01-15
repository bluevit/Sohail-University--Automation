from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import shutil
import threading
import traceback
import full_pipeline
from werkzeug.utils import secure_filename

# ===============================
# CONFIG
# ===============================
UPLOAD_FOLDER = "uploads"
PROCESS_FOLDER = "teacherEval"

app = Flask(__name__)
CORS(app, origins=["http://127.0.0.1:5500"])

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROCESS_FOLDER, exist_ok=True)

# ===============================
# HEALTH CHECK
# ===============================
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "live"}), 200


# ===============================
# BACKGROUND WORKER
# ===============================
def run_pipeline_safe(pdf_path, batch_code, semester, session):
    try:
        print("🚀 Pipeline started")
        print("📦 Batch Code:", batch_code)
        print("📘 Semester:", semester)
        print("🗓️ Session:", session)
        full_pipeline.process_single_pdf(
            pdf_path,
            batch_code=batch_code,
            semester=semester,
            session=session
        )
        full_pipeline.clean_results_json()

        print("✅ Pipeline finished successfully")
    except Exception:
        print("🔥 PIPELINE ERROR")
        traceback.print_exc()


# ===============================
# UPLOAD API
# ===============================

@app.route("/upload", methods=["POST"])
def upload_pdf():
    file = request.files.get("pdf")
    batch_code = request.form.get("batch_code")
    semester = request.form.get("semester")
    session = request.form.get("session")

    if not file or not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Invalid PDF"}), 400

    if not batch_code or not semester:
        return jsonify({"error": "Batch code and semester required"}), 400

    filename = secure_filename(file.filename)
    upload_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(upload_path)

    final_path = os.path.join(PROCESS_FOLDER, filename)
    shutil.move(upload_path, final_path)

    # ✅ RUN PIPELINE IN BACKGROUND
    thread = threading.Thread(
        target=run_pipeline_safe,
        args=(final_path, batch_code, semester, session),
        daemon=True
    ).start()

    return jsonify({
        "message": "Upload successful. Processing started in background."
    }), 200


# ===============================
# RUN SERVER
# ===============================
if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=False,
        use_reloader=False,
        threaded=True
    )
