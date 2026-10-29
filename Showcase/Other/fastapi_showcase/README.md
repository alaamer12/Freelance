# أكاديمية المستقبل الرقمي (Digital Future Academy) - FastAPI Showcase

A modern Arabic RTL web application built with **FastAPI** and **Jinja2 Templates** featuring an interactive educational platform and smart learning dashboard.

---

## 📋 Project Features

- **لوحة التحكم الرئيسية (Dashboard - `/`)**: Overview of student statistics, active courses, learning paths, and quick actions.
- **الدورات التدريبية (Courses - `/courses`)**: Course catalog, enrollments, and syllabus overview.
- **إدارة الطلاب (Students - `/students`)**: Student directory, enrollment records, and progress metrics.
- **المدربين (Instructors - `/instructors`)**: Instructor profiles, courses taught, and ratings.
- **التقييمات والامتحانات (Assessments - `/assessments`)**: Quizzes, assignments, grades, and upcoming exams.
- **الشهادات (Certificates - `/certificates`)**: Issued certificates, verification, and achievements.
- **تحليلات التعلم (Analytics - `/analytics`)**: Educational metrics, performance graphs, and engagement trends.
- **الملف الشخصي (Profile - `/profile`)**: User profile, settings, and personal details.
- **Showcase API Endpoints**:
  - `GET /api/dashboard/stats`: Platform statistics.
  - `GET /api/courses`: Available courses data.
  - `GET /api/students`: Students list and progress.
- **Interactive API Documentation**:
  - Swagger UI: `http://127.0.0.1:6000/docs`
  - ReDoc: `http://127.0.0.1:6000/redoc`

---

## 🛠️ Prerequisites

- **Python 3.10+** (or Python 3.8+)
- **pip** (Python package manager)

---

## 🚀 How to Run the Project

### 1. Open Terminal in the Project Directory
Navigate to the root directory where `main.py` is located:
```bash
cd "E:\Freelance\Code Snippets\fastapi_showcase"
```

---

### 2. Activate or Create Virtual Environment

If using the existing `.venv` in the folder:

- **On Windows (PowerShell):**
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```
- **On Windows (Command Prompt `cmd`):**
  ```cmd
  .venv\Scripts\activate.bat
  ```
- **On macOS / Linux:**
  ```bash
  source .venv/bin/activate
  ```

*(To create a fresh virtual environment if needed: `python -m venv venv` and activate it).*

---

### 3. Install Dependencies
Ensure all required packages are installed:
```bash
pip install -r requirements.txt
```

*(Dependencies include: `fastapi`, `uvicorn[standard]`, `jinja2`, `python-multipart`, and `aiofiles`)*

---

### 4. Start the Application

You can start the server using either method below:

#### Method A: Direct Execution with Python
```bash
python main.py
```
*(Runs by default on port `6000` as configured in `main.py`)*

#### Method B: Using Uvicorn CLI (with Auto-Reload)
```bash
uvicorn main:app --reload --port 6000
```
*(Or specify any port, e.g. `--port 8000`)*

---

### 5. Access the Platform

Open your web browser and navigate to:
- 🌐 **Web Dashboard:** [http://127.0.0.1:6000/](http://127.0.0.1:6000/)
- 📚 **Interactive Swagger API Docs:** [http://127.0.0.1:6000/docs](http://127.0.0.1:6000/docs)
- 📖 **ReDoc Documentation:** [http://127.0.0.1:6000/redoc](http://127.0.0.1:6000/redoc)

---

## 📁 Directory Structure

```text
fastapi_showcase/
├── main.py                     # FastAPI application instance, routes & API endpoints
├── requirements.txt            # Python dependencies
├── README.md                   # Setup guide and project documentation
├── static/                     # Static files (CSS, JS, Images, Fonts)
└── templates/                  # Jinja2 HTML Templates (Arabic RTL)
    ├── analytics.html          # Learning analytics page
    ├── assessments.html        # Assessments and exams page
    ├── base.html               # Main base layout with navbar & sidebar
    ├── certificates.html       # Certificates showcase
    ├── courses.html            # Courses catalog page
    ├── dashboard.html          # Main platform dashboard
    ├── instructors.html        # Instructors directory
    ├── profile.html            # User profile page
    └── students.html           # Students management page
```
