# Notveya

A notes & video sharing platform for classrooms, built with Flask and MySQL.

- **Teachers** create classrooms, add students, and upload notes/videos.
- **Students** join classrooms with a code, download materials, and rate them.
- Everyone can edit their profile (photo, bio, school).
- Sign up/log in with email+password, or with **Google**.

## 1. Requirements

- Python 3.10+
- MySQL Server 8.x (or MariaDB) running locally or remotely
- A Google Cloud project, if you want Google sign-in (optional but requested)

## 2. Set up the database

Log into MySQL and create a database + user for the app:

```sql
CREATE DATABASE notveya CHARACTER SET utf8mb4;
CREATE USER 'notveya_user'@'localhost' IDENTIFIED BY 'notveya_pass';
GRANT ALL PRIVILEGES ON notveya.* TO 'notveya_user'@'localhost';
FLUSH PRIVILEGES;
```

The app creates all tables automatically on first run (`db.create_all()`), so you
don't need to write any schema by hand — just make sure the database itself exists.

## 3. Install dependencies

```bash
cd notveya
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## 4. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`:

- `SECRET_KEY` — any long random string.
- `DATABASE_URL` — `mysql+pymysql://notveya_user:notveya_pass@localhost:3306/notveya`
  (match whatever you created in step 2).
- `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` — see step 5.

## 5. Set up Google Sign-In (optional)

1. Go to the [Google Cloud Console](https://console.cloud.google.com/apis/credentials).
2. Create an **OAuth client ID** of type "Web application".
3. Add this **Authorized redirect URI**: `http://localhost:5000/auth/google/callback`
   (swap the host/port for wherever you deploy).
4. Copy the generated Client ID and Client Secret into `.env`.

If you skip this, the site still works fully with email/password accounts —
the "Continue with Google" buttons will just show an error until it's configured.

## 6. Run it

```bash
python app.py
```

Visit **http://localhost:5000**.

## How the pieces fit together

```
app.py               # application factory, registers blueprints
config.py             # reads .env, MySQL URI, upload folders/limits
extensions.py          # db, login_manager, oauth singletons
models.py              # User, Classroom, Enrollment, Material, Rating
routes/
  auth.py              # register, login, logout, Google OAuth
  main.py               # landing page, dashboard, profile, download/rate
  teacher.py            # create classroom, roster, upload/delete materials
  student.py            # join classroom, view classroom
templates/              # Jinja templates (shared base.html + per-page views)
static/css/style.css      # the whole visual design
static/uploads/            # uploaded profile pictures & classroom materials
```

## Notes on what's intentionally simple

This is a solid working starting point, not a production hardened deployment.
A few things worth upgrading before going live:

- **File storage**: uploads are saved to local disk (`static/uploads/`). For
  production, point `MATERIAL_FOLDER`/`PROFILE_PIC_FOLDER` at cloud storage
  (S3, GCS, etc.) instead.
- **Adding students**: a teacher currently adds a student by their exact
  account email (the student must have already signed up), or the student
  joins themselves with the classroom code. You could extend this with
  email invitations for students who haven't signed up yet.
- **Validation/rate limiting**: basic server-side checks are in place, but
  there's no CSRF token library, virus scanning on uploads, or rate limiting
  on login attempts — add `Flask-WTF` and `Flask-Limiter` before deploying
  publicly.
- **Migrations**: the app uses `db.create_all()` for simplicity. For a real
  project, switch to `Flask-Migrate`/Alembic so schema changes don't require
  dropping tables.
