from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import uvicorn

app = FastAPI(
    title="أكاديمية المستقبل الرقمي - منصة التعلم الذكي",
    description="منصة تعليمية متطورة للتدريب والتطوير المهني باستخدام الذكاء الاصطناعي",
    version="1.0.0"
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """لوحة التحكم الرئيسية"""
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/courses", response_class=HTMLResponse)
async def courses(request: Request):
    """صفحة الدورات التدريبية"""
    return templates.TemplateResponse("courses.html", {"request": request})

@app.get("/students", response_class=HTMLResponse)
async def students(request: Request):
    """صفحة إدارة الطلاب"""
    return templates.TemplateResponse("students.html", {"request": request})

@app.get("/instructors", response_class=HTMLResponse)
async def instructors(request: Request):
    """صفحة المدربين"""
    return templates.TemplateResponse("instructors.html", {"request": request})

@app.get("/assessments", response_class=HTMLResponse)
async def assessments(request: Request):
    """صفحة التقييمات والامتحانات"""
    return templates.TemplateResponse("assessments.html", {"request": request})

@app.get("/certificates", response_class=HTMLResponse)
async def certificates(request: Request):
    """صفحة الشهادات"""
    return templates.TemplateResponse("certificates.html", {"request": request})

@app.get("/analytics", response_class=HTMLResponse)
async def analytics(request: Request):
    """صفحة تحليلات التعلم"""
    return templates.TemplateResponse("analytics.html", {"request": request})

@app.get("/profile", response_class=HTMLResponse)
async def profile(request: Request):
    """صفحة الملف الشخصي"""
    return templates.TemplateResponse("profile.html", {"request": request})

# API Endpoints for data (non-functional, just for showcase)
@app.get("/api/dashboard/stats")
async def get_dashboard_stats():
    """إحصائيات لوحة التحكم"""
    return {
        "total_students": 2847,
        "active_courses": 156,
        "completion_rate": 87.3,
        "certificates_issued": 1249
    }

@app.get("/api/courses")
async def get_courses():
    """قائمة الدورات"""
    return {
        "courses": [
            {
                "id": 1,
                "title": "تطوير تطبيقات الويب المتقدمة",
                "instructor": "د. أحمد السالم",
                "students": 145,
                "duration": "8 أسابيع",
                "level": "متقدم"
            },
            {
                "id": 2,
                "title": "أساسيات الذكاء الاصطناعي",
                "instructor": "د. فاطمة النور",
                "students": 203,
                "duration": "12 أسبوع",
                "level": "مبتدئ"
            }
        ]
    }

@app.get("/api/students")
async def get_students():
    """قائمة الطلاب"""
    return {
        "students": [
            {
                "id": 1,
                "name": "محمد العتيبي",
                "email": "mohammed@email.com",
                "courses_enrolled": 3,
                "progress": 75,
                "level": "متوسط"
            },
            {
                "id": 2,
                "name": "سارة الأحمد",
                "email": "sara@email.com", 
                "courses_enrolled": 2,
                "progress": 92,
                "level": "متقدم"
            }
        ]
    }

if __name__ == "__main__":
    uvicorn.run(app, port=6000)
