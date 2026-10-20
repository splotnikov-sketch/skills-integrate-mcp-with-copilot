# Mergington High School Activities API

A super simple FastAPI application that allows students to view and sign up for extracurricular activities.

## Features

- View all available extracurricular activities
- Sign up for activities
- Public activity and participant browsing; teacher-only registration changes
- Teacher login and logout with one-hour sessions

## Getting Started

1. Install the dependencies:

   ```
   pip install -r requirements.txt
   ```

2. From the repository root, assign a teacher username and password:

   ```
   python -m src.manage_teachers teacher
   ```

   The command prompts for a password and stores only a salted PBKDF2-SHA256
   hash in the gitignored `src/teachers.json`. Repeat it to add teachers or
   change passwords. `teachers.example.json` shows the empty JSON structure;
   there are no default accounts or passwords. Set `TEACHERS_FILE` to use
   another location. Never commit real credentials or credential files.

3. Run the application from the repository root:

   ```
   uvicorn src.app:app --reload
   ```

4. Open http://localhost:8000. Use the account icon in the top right, then
   **Teacher login**. Students can still browse activities and participant lists.
   Registration and removal controls appear only after teacher login.

   API documentation:
   - API documentation: http://localhost:8000/docs
   - Alternative documentation: http://localhost:8000/redoc

## API Endpoints

| Method | Endpoint                                                          | Description                                                         |
| ------ | ----------------------------------------------------------------- | ------------------------------------------------------------------- |
| GET    | `/activities`                                                     | Get all activities with their details and current participant count |
| POST   | `/activities/{activity_name}/signup?email=student@mergington.edu` | Sign up for an activity                                             |
| DELETE | `/activities/{activity_name}/unregister?email=student@mergington.edu` | Unregister a student |
| POST | `/auth/login` | Accept JSON username/password and return a bearer token |
| POST | `/auth/logout` | Revoke the current bearer token |

Signup, unregister, and logout require `Authorization: Bearer <access_token>`.
The frontend keeps the token in memory, not browser storage. Reloading the page
requires logging in again. Expired sessions switch the UI back to student view
when a registration request is rejected.

Sessions are in memory, expire after one hour, and are revoked on logout or
server restart. Restart after changing/removing credentials to revoke old
sessions. Use a single server worker for this exercise. A production deployment
needs HTTPS, login rate limiting, and a shared session store for multiple workers.
Missing or malformed teacher configuration disables login with an explicit error;
public browsing remains available.

## Tests

From the repository root:

```
pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

## Data Model

The application uses a simple data model with meaningful identifiers:

1. **Activities** - Uses activity name as identifier:

   - Description
   - Schedule
   - Maximum number of participants allowed
   - List of student emails who are signed up

2. **Students** - Uses email as identifier:
   - Name
   - Grade level

All data is stored in memory, which means data will be reset when the server restarts.
