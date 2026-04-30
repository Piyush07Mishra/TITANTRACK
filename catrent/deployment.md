# Deployment Guide - CatRent Project

Yes, you can deploy this project for **FREE** using modern cloud platforms. This guide outlines the best free-tier stack and the steps to get your application live.

## 🚀 Recommended Free Stack
- **Web Hosting**: [Render](https://render.com/) (Recommended for modern workflow) OR [PythonAnywhere](https://www.pythonanywhere.com/) (Great for beginner-friendly Django setup)
- **Database**: [Neon DB](https://neon.tech/) (for Render) OR **SQLite/MySQL** (for PythonAnywhere)
- **Media Storage**: [Cloudinary](https://cloudinary.com/) (Free Tier - already integrated in your code)
- **Static Files**: WhiteNoise (Middleware to serve CSS/JS directly from Django)

---

## 🛠️ Phase 1: Project Preparation

Before deploying, we need to make the project "Production Ready".

### 1. Create a `.gitignore` file
Ensure you don't upload sensitive data or local databases to GitHub.
```bash
# .gitignore
.env
db.sqlite3
__pycache__/
*.pyc
media/
qr_codes/
.vscode/
```

### 2. Update `requirements.txt`
Render and other platforms need `gunicorn` (web server) and `whitenoise` (for static files).
Add these to your `requirements.txt`:
```text
gunicorn
whitenoise
```

### 3. Configure `settings.py` for Static Files
Add WhiteNoise to your middleware in `catrent/settings.py`:
```python
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Add this right after SecurityMiddleware
    # ... other middleware ...
]

# Add Static Root at the bottom
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
```

---

## 💾 Phase 2: Setup Database (Neon DB)

Neon offers a serverless PostgreSQL database with a generous free tier that is perfect for Django.

1. Create a free account on [Neon.tech](https://neon.tech/).
2. Create a new project (e.g., `catrent-db`).
3. In the Neon Dashboard, look for the **Connection Details** section.
4. Ensure **Pooled Connection** is checked (recommended for serverless apps).
5. Copy the **Connection String** (URI). It looks like: `postgresql://alex:password@ep-cool-darkness-123.us-east-2.aws.neon.tech/neondb?sslmode=require`.
6. Save this URI for the Render environment variables.

---

## 🌐 Phase 3: Deploy to Render

### 1. Push to GitHub
Create a private repository on GitHub and push your code there.

### 2. Create Render Web Service
1. Login to [Render](https://dashboard.render.com/).
2. Click **New +** > **Web Service**.
3. Connect your GitHub repository.
4. **Settings:**
   - **Runtime**: `Python`
   - **Build Command**: `pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate`
   - **Start Command**: `gunicorn catrent.wsgi:application`

### 3. Set Environment Variables
In the Render dashboard, go to the **Environment** tab and add:
- `DJANGO_SECRET_KEY`: (A random long string)
- `DEBUG`: `False`
- `DATABASE_URL`: (Your Neon DB Connection String)
- `CLOUDINARY_CLOUD_NAME`: (From your Cloudinary account)
- `CLOUDINARY_API_KEY`: (From your Cloudinary account)
- `CLOUDINARY_API_SECRET`: (From your Cloudinary account)
- `ADMIN_SIGNUP_KEY`: (Your secret key for admin creation)
- `EMAIL_HOST_PASSWORD`: (Your Gmail App Password)

---

## 🔍 Phase 4: Post-Deployment
Once the build is successful:
1. Access your site at `https://your-app-name.onrender.com`.
2. Create your first admin user via the signup page using your `ADMIN_SIGNUP_KEY`.
3. Verify that images (QR codes) are being saved to Cloudinary.

---

---

## 🐍 Option 2: Deploy to PythonAnywhere

PythonAnywhere is a dedicated Python hosting platform. It is excellent because it has a **persistent file system**, meaning you can use your `db.sqlite3` file and it won't disappear.

### 1. Upload your code
1. Create a free account on [PythonAnywhere](https://www.pythonanywhere.com/).
2. Go to the **Consoles** tab and open a **Bash** console.
3. Clone your GitHub repository: `git clone https://github.com/your-username/your-repo.git`.

### 2. Create a Virtual Environment
In the Bash console:
```bash
cd your-repo-name
mkvirtualenv --python=/usr/bin/python3.10 myenv
pip install -r requirements.txt
```

### 3. Setup the Web App
1. Go to the **Web** tab in PythonAnywhere dashboard.
2. Click **Add a new web app**.
3. Choose **Manual Configuration** (do NOT choose Django, as we have an existing project).
4. Choose **Python 3.10**.
5. After creation, scroll down to **Virtualenv** and enter the path: `/home/yourusername/.virtualenvs/myenv`.

### 4. Configure WSGI File
1. In the **Web** tab, click the link to "WSGI configuration file".
2. Delete everything and paste this (replace `yourusername` and `your-repo-name`):
```python
import os
import sys

path = '/home/yourusername/your-repo-name'
if path not in sys.path:
    sys.path.append(path)

os.environ['DJANGO_SETTINGS_MODULE'] = 'catrent.settings'

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()
```

### 5. Static Files
In the **Web** tab, scroll to **Static files** and add:
- **URL**: `/static/`
- **Path**: `/home/yourusername/your-repo-name/staticfiles`

Run `python manage.py collectstatic` in your console before reloading.

### 6. Environment Variables
PythonAnywhere doesn't have an "Environment" tab like Render. You must add them to your WSGI file or use a `.env` file. Since your code already loads `.env` files (see `settings.py:39`), just create a `.env` file in your project folder on PythonAnywhere.

---

## ⚠️ Important Notes
- **Cold Starts**: Render's free tier spins down after 15 minutes of inactivity.
- **SQLite on PythonAnywhere**: This is perfectly fine and safe! PythonAnywhere does not delete your files.
- **Neon DB on PythonAnywhere**: The free tier of PythonAnywhere blocks most external database connections. If you use PythonAnywhere's free tier, stick to **SQLite**.
