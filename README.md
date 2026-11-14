# 🏙️ AI City Management Platform SMART_LAND

### Intelligent Municipal Complaint Management, Public Infrastructure Monitoring & Smart City Operations

An AI-powered municipal management platform designed to connect citizens, government officials, and field workers through a unified digital system. The platform streamlines civic complaint reporting, automates complaint analysis and prioritization, improves municipal task allocation, and provides real-time visibility into city infrastructure and public services.

**Project:** AI City Management Platform  
**Team:** DoomNdebug – Team Diamond  
**Category:** Artificial Intelligence / Smart City / Civic Technology

---

## 📌 Table of Contents

1. [Overview](#-overview)
2. [Problem Statement](#-problem-statement)
3. [Our Solution](#-our-solution)
4. [Key Features](#-key-features)
5. [User Roles](#-user-roles)
6. [AI Integration](#-ai-integration)
7. [Technology Stack](#-technology-stack)
8. [System Architecture](#-system-architecture)
9. [Project Structure](#-project-structure)
10. [Database Design](#-database-design)
11. [API Overview](#-api-overview)
12. [Installation and Setup](#-installation-and-setup)
13. [Environment Configuration](#-environment-configuration)
14. [Running the Application](#-running-the-application)
15. [Security and Privacy](#-security-and-privacy)
16. [Testing](#-testing)
17. [Demo Workflow](#-demo-workflow)
18. [Future Scope](#-future-scope)
19. [Team Responsibilities](#-team-responsibilities)

---

## 🌆 Overview

Traditional municipal complaint management systems often rely on disconnected processes, manual complaint classification, delayed task allocation, and limited communication between citizens and municipal departments.

The AI City Management Platform addresses these challenges through a centralized, intelligent system that brings together:

- Citizen complaint reporting and tracking.
- AI-assisted complaint classification and prioritization.
- Duplicate complaint identification.
- Department and field-worker assignment.
- Public infrastructure project monitoring.
- Safety hazard reporting.
- Interactive city maps and traffic hotspot visualization.
- Role-based dashboards and analytics.

The platform aims to make municipal operations more transparent, organized, data-driven, and responsive to citizens' needs.

## ❗ Problem Statement

Municipal administrations face several operational challenges:

- Citizens lack a centralized and transparent way to report civic issues.
- Complaints are frequently categorized and routed manually.
- Duplicate complaints increase administrative workload.
- High-priority infrastructure and safety issues may not receive timely attention.
- Officials have limited visibility into department-level complaint performance.
- Field-worker allocation and task tracking can be difficult to coordinate.
- Citizens have limited visibility into ongoing infrastructure projects.
- Safety-related infrastructure hazards may remain unreported or unresolved.

These challenges result in inefficient workflows, delayed responses, and reduced public trust.

## 💡 Our Solution

The AI City Management Platform provides a unified municipal operations system with three primary user interfaces:

**Citizen Portal:** Allows citizens to report civic problems, upload photographic evidence, track complaints, explore infrastructure projects, submit feedback, and report public safety hazards.

**Official Portal:** Enables municipal officials to monitor complaints, manage departments, assign work, track projects, analyze performance, and manage safety reports according to their permissions.

**Worker Access:** Provides field workers with access to their dashboard and assigned tasks, allowing them to track and update their work.

AI services assist the municipal workflow by analyzing complaints, identifying potential duplicates, and supporting priority calculation.

---

## 🚀 Key Features

### 1. Citizen Portal

- Citizen registration and authentication.
- Personalized citizen dashboard.
- Complaint reporting with photographic evidence.
- AI-assisted complaint categorization.
- Automatic department routing.
- Complaint priority and severity assessment.
- Complaint history and status tracking.
- Complaint status update timeline.
- Public infrastructure project listing.
- Citizen feedback submission.
- Interactive 2D city map.
- Safety hazard reporting.
- Personal safety-report history.
- Profile information and account settings.

### 2. AI-Powered Complaint Management

- AI-assisted complaint analysis.
- Automatic identification of complaint categories.
- Complaint title and summary generation.
- Severity assessment.
- Potential duplicate complaint identification.
- Priority calculation based on severity, duplicate reports, and overdue conditions.
- Department resolution based on complaint classification.
- Deterministic fallback handling when an AI provider is unavailable.

### 3. Official Portal

- Role-based official authentication.
- Municipal and department dashboards.
- Complaint register and filtering.
- Complaint details and status history.
- Complaint status management.
- Department assignment.
- Duplicate complaint linking.
- Project creation and management.
- Citizen feedback management.
- Feedback-to-complaint conversion.
- Worker directory.
- Worker and field-task assignments.
- Assignment progress tracking.
- Safety report register for authorized safety officers.
- Department and priority analytics.
- Interactive infrastructure and complaint map.

### 4. Worker Access

- Worker-specific dashboard.
- View assigned tasks.
- View complaint or traffic-hotspot task details.
- Update assignment progress.
- Track assignment completion.

### 5. Smart City Map

The interactive 2D map provides a geographical view of supported municipal information.

Map layers include:

- Civic complaint locations.
- Infrastructure projects.
- Traffic hotspots.
- Aggregated public safety zones.

The map uses privacy-preserving responses for citizen-facing information. Traffic hotspot information may contain seeded demonstration data and should not be interpreted as a live traffic feed.

### 6. Safety Reporting

Citizens can report public infrastructure hazards such as:

- Poorly illuminated streets.
- Non-functional streetlights.
- Unsafe crossings.
- Dark or deserted public locations.
- Poorly lit bus stops.
- Other infrastructure-related safety concerns.

Safety officers can access the restricted safety register, review reports, update report statuses, and manage the associated municipal workflow.

---

## 👥 User Roles

| Role | Responsibilities |
|---|---|
| Citizen | Report complaints, track issues, view projects, submit feedback, and report safety hazards. |
| Official | Manage complaints, departments, projects, feedback, and worker assignments within authorized scope. |
| Safety Officer | Perform authorized safety-report monitoring and management in addition to permitted official operations. |
| Field Worker | View and update assigned municipal tasks. |

Access is controlled by backend authentication and role-based authorization.

---

## 🧠 AI Integration

Artificial intelligence is integrated into the municipal complaint workflow to reduce manual processing and assist officials in making informed decisions.

### AI Complaint Analysis

When a citizen submits a complaint, the backend invokes the AI analysis service.

The AI-assisted workflow supports:

1. Understanding the submitted complaint description.
2. Identifying the appropriate complaint category.
3. Generating a structured title and summary.
4. Assessing complaint severity.
5. Supporting department routing.
6. Identifying potential duplicate complaints.

### Duplicate Detection

The platform identifies potentially similar complaints to help officials recognize repeated reports about the same civic issue.

Duplicate detection is advisory. Authorized officials review and link duplicate complaints rather than having the system automatically merge unrelated reports.

### Priority Calculation

The backend calculates complaint priority using severity, duplicate report count, and overdue conditions.

The implemented calculation is:

`Priority Score = (Severity × 10) + ((Report Count - 1) × 5) + Overdue Bonus`

Priority tiers:

| Score | Priority |
|---|---|
| 80 and above | Critical |
| 60–79 | High |
| 35–59 | Medium |
| Below 35 | Low |

The final priority calculation is handled by the backend.

### AI Failure Handling

AI services are designed with fallback behavior so that a temporary AI-provider failure does not necessarily prevent complaint submission.

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | React, Vite, JavaScript |
| UI Styling | CSS |
| Interactive Mapping | MapLibre GL |
| Backend | Python, FastAPI |
| Database | Supabase PostgreSQL |
| Authentication | Supabase Auth, JWT |
| File Storage | Supabase Storage |
| AI Integration | AI analysis service integrated through the backend |
| API Communication | Axios, REST APIs |
| API Documentation | OpenAPI, Swagger UI |
| Testing | Pytest, frontend build and lint checks |
| Version Control | Git, GitHub |

---

## 🏗️ System Architecture

The platform follows a client-server architecture.

```text
                  AI CITY MANAGEMENT PLATFORM
                              |
              +---------------+---------------+
              |                               |
         React Frontend                 FastAPI Backend
              |                               |
       +------+------+              +---------+---------+
       |      |      |              |         |         |
    Citizen Official Worker      Auth     API Routes  AI Services
     Portal  Portal  Access        |         |         |
       |      |      |              |         |         |
       +------+------+              +---------+---------+
              |                               |
          Axios REST API                 Service Layer
                                              |
                                    +---------+---------+
                                    |                   |
                              Supabase DB         Supabase Storage
                              PostgreSQL           Complaint Images
                                    |
                              Role-Based Access
```

### Request Flow

1. A user authenticates through the frontend.
2. The backend validates the access token.
3. The backend identifies the authenticated user's profile and role.
4. The frontend sends requests through the centralized API client.
5. Backend routes invoke the appropriate service functions.
6. Services interact with Supabase or AI components.
7. The backend returns structured responses.
8. The frontend displays the results according to the user's permissions.

---

## 📁 Project Structure

The repository is organized into frontend, backend, database, documentation, and testing components.

```text
AI-City-Management-Platform/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── auth.py
│   │   │       ├── complaints.py
│   │   │       ├── projects.py
│   │   │       ├── feedback.py
│   │   │       ├── map.py
│   │   │       ├── safety.py
│   │   │       ├── dashboard.py
│   │   │       ├── workers.py
│   │   │       └── assignments.py
│   │   │
│   │   ├── database/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   │
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── context/
│   │   ├── data/
│   │   ├── pages/
│   │   │   ├── citizen/
│   │   │   └── official/
│   │   ├── routes/
│   │   ├── services/
│   │   │   ├── api.js
│   │   │   ├── authService.js
│   │   │   ├── citizenService.js
│   │   │   └── officialService.js
│   │   └── ...
│   │
│   ├── package.json
│   └── vite.config.js
│
├── database/
│   ├── schema.sql
│   └── seed.sql
│
├── docs/
│   ├── PRD.md
│   └── DoomNdebug_TeamDiamond_Team_Allocation_and_Execution_Plan.md
│
├── scratch/
│   └── ...
│
└── README.md
```

*This is the intended high-level structure. Refer to the repository for the exact current file layout.*

---

## 🗄️ Database Design

The platform uses Supabase PostgreSQL for persistent storage.

Important database tables include:

| Table | Purpose |
|---|---|
| `profiles` | User profile and role information. |
| `departments` | Municipal department records. |
| `complaints` | Civic complaint information and status. |
| `complaint_updates` | Complaint status history and remarks. |
| `projects` | Municipal infrastructure projects. |
| `project_feedback` | Citizen feedback on infrastructure projects. |
| `workers` | Field-worker records and availability. |
| `assignments` | Worker task assignments. |
| `traffic_hotspots` | Traffic hotspot information. |

### Database Features

- UUID-based identifiers.
- Foreign-key relationships.
- Role-based access control.
- Row Level Security (RLS).
- Complaint status history.
- Department relationships.
- Worker and assignment relationships.
- Supabase Storage integration for complaint images.

The backend uses authorized database access and enforces application-level permissions. Service-role credentials must remain private.

### Complaint Image Storage

Complaint images are stored in a private Supabase Storage bucket.

Expected constraints:
- Supported formats: JPEG, PNG, WebP.
- Maximum image size: 5 MB.
- User-namespaced storage paths.
- Authorized access through signed URLs.

---

## 🔌 API Overview

The backend exposes REST APIs under:

`/api/v1`

### Authentication

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/auth/register` | Register a citizen. |
| POST | `/auth/login` | Authenticate a user. |
| GET | `/auth/me` | Retrieve authenticated profile. |

### Complaints

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/complaints` | Submit a complaint. |
| GET | `/complaints/my` | Retrieve citizen complaints. |
| GET | `/complaints` | Official complaint register. |
| GET | `/complaints/{id}` | Retrieve complaint details. |
| PATCH | `/complaints/{id}` | Update permitted complaint fields. |
| PATCH | `/complaints/{id}/status` | Update complaint status. |
| POST | `/complaints/{id}/assign` | Assign complaint to a department. |
| GET | `/complaints/{id}/updates` | Retrieve status history. |
| POST | `/complaints/{id}/link-duplicate` | Link a duplicate complaint. |
| POST | `/complaints/upload-image` | Upload complaint evidence. |

### Projects and Feedback

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/projects` | Retrieve available projects. |
| POST | `/projects` | Create a project. |
| GET | `/projects/{id}` | Retrieve project details. |
| PATCH | `/projects/{id}` | Update project information. |
| POST | `/feedback` | Submit citizen feedback. |
| GET | `/feedback` | Retrieve feedback for authorized officials. |
| POST | `/feedback/{id}/convert-to-complaint` | Convert actionable feedback into a complaint. |

### Map and Traffic

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/map/complaints` | Retrieve map complaint markers. |
| GET | `/map/projects` | Retrieve project map markers. |
| GET | `/map/hotspots` | Retrieve traffic hotspots. |
| POST | `/map/hotspots` | Create a hotspot record. |
| GET | `/map/safety-zones` | Retrieve aggregated safety zones. |

### Safety Reports

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/safety-reports` | Submit a safety report. |
| GET | `/safety-reports/mine` | Retrieve citizen's own safety reports. |
| GET | `/safety-reports` | Retrieve authorized safety register. |
| GET | `/safety-reports/{id}` | Retrieve safety report details. |
| PATCH | `/safety-reports/{id}` | Update an authorized safety report. |

### Dashboard

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/dashboard/summary` | Role-specific dashboard metrics. |
| GET | `/dashboard/departments` | Department-level metrics. |
| GET | `/dashboard/priorities` | Complaint priority metrics. |
| GET | `/dashboard/safety` | Safety dashboard metrics for authorized officers. |

### Workers and Assignments

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/workers` | Retrieve authorized worker records. |
| POST | `/assignments` | Create a worker assignment. |
| GET | `/assignments` | Retrieve authorized assignments. |
| PATCH | `/assignments/{assignment_id}` | Update an assignment. |

For complete request and response schemas, visit the Swagger documentation.

---

## ⚙️ Installation and Setup

### Prerequisites

Install the following:

- Python 3.10 or later (use the version supported by the backend dependencies).
- Node.js and npm.
- Git.
- A Supabase project.
- Required AI-provider credentials configured for the backend.

### 1. Clone the Repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd <YOUR_REPOSITORY_NAME>
```

### 2. Backend Setup

Navigate to the backend directory:

```bash
cd backend
```

Create a virtual environment:

**Windows PowerShell**

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**Linux / macOS**

```bash
python3 -m venv venv
source venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure environment variables using the provided example:

```bash
cp .env.example .env
```

On Windows PowerShell, you can also copy the file using:

```powershell
Copy-Item .env.example .env
```

Fill in the required values in `backend/.env`.

### 3. Database Setup

1. Create a Supabase project.
2. Open the Supabase SQL Editor.
3. Review `database/schema.sql`.
4. Execute the reviewed schema to create the required tables, relationships, policies, and database functions.
5. Review `database/seed.sql` before executing it.
6. Configure the required Supabase Storage bucket for complaint images.
7. Configure backend environment variables.

**Important:** The seed script does not create Supabase Auth users or passwords. Demo accounts must be provisioned separately through an authorized process.

### 4. Frontend Setup

Open a separate terminal:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

Create the frontend environment file if required by the project:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

Vite environment variables are read during the build process. Restart the development server after changing them.

---

## ▶️ Running the Application

Both servers must run simultaneously.

### Start the Backend

From the `backend` directory:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend:

`http://127.0.0.1:8000`

API health check:

`http://127.0.0.1:8000/health`

Swagger documentation:

`http://127.0.0.1:8000/docs`

### Start the Frontend

From the `frontend` directory:

```bash
npm run dev
```

Frontend:

`http://localhost:5173`

### Verify Connectivity

1. Open the frontend URL.
2. Sign in using a provisioned account.
3. Confirm the backend health endpoint responds successfully.
4. Open Swagger to inspect available APIs.
5. Test a role-authorized workflow.

---

## 🔐 Environment Configuration

The backend uses environment variables for database access, authentication, and AI services.

Refer to `backend/.env.example` for the exact required variable names.

Typical configuration categories include:

| Configuration | Purpose |
|---|---|
| Supabase URL | Supabase project endpoint. |
| Supabase anon key | Public client/project key where required. |
| Supabase service-role key | Privileged backend database operations. |
| JWT configuration | Authentication token validation. |
| AI provider key | Access to the configured AI service. |
| CORS configuration | Permitted frontend origins. |

**Security rules:**

- Never commit `.env` files.
- Never expose the Supabase service-role key in frontend code.
- Never place private AI credentials in Vite environment variables.
- Keep production secrets in the deployment provider's environment configuration.
- Use HTTPS for production deployments.

---

## 🛡️ Security and Privacy

Security is enforced primarily by the backend.

### Authentication

- Supabase Auth-based authentication.
- JWT validation on protected endpoints.
- Profile information retrieved from the authenticated identity.

### Role-Based Authorization

- Citizens can access their own complaints and safety reports.
- Officials are restricted by their department scope where applicable.
- Workers can access only their authorized assignments and worker-specific data.
- Safety registers are restricted to designated safety officers.

### Data Privacy

- Public map responses avoid exposing private citizen information.
- Public safety-zone information is aggregated.
- Privileged safety information is not exposed through citizen-facing APIs.
- Complaint image storage uses private access and signed URLs.
- Backend authorization is enforced even when frontend route protection is present.

---

## 🧪 Testing

The project includes backend and frontend verification.

### Frontend

```bash
cd frontend
npm run build
npm run lint
```

### Backend

Run the relevant test suites from the repository root using the configured Python environment.

Example:

```bash
pytest
```

Additional focused regression scripts may be available in `scratch/`, including:

- Authentication contract tests.
- Citizen integration tests.
- Worker and assignment tests.
- AI regression tests.

Run the specific test scripts documented in the current repository before a release.

### Important Testing Distinction

- Unit tests verify individual functions and business logic.
- Contract tests verify request and response structures.
- Mock integration tests verify behavior using simulated responses.
- Live integration tests verify actual communication with configured backend services.

A passing mock test does not by itself prove that a feature works against live Supabase services.

---

## 🎬 Demo Workflow

A suggested demonstration sequence:

### Citizen Workflow

1. Register or log in as a citizen.
2. Open the citizen dashboard.
3. Submit a civic complaint with a description and photograph.
4. Demonstrate AI-assisted complaint analysis and priority assessment.
5. Open My Complaints.
6. View the complaint's status history.
7. Explore infrastructure projects.
8. Submit feedback on a project.
9. Open the interactive city map.
10. Submit a safety hazard report.

### Official Workflow

1. Log in as an authorized municipal official.
2. Open the official dashboard.
3. View department complaint statistics.
4. Open the complaint register.
5. Inspect a complaint and its AI assessment.
6. Update complaint status.
7. Assign a complaint to a department.
8. Create a field-worker assignment.
9. Review project feedback.
10. Manage infrastructure projects.

### Worker Workflow

1. Log in using a provisioned worker account.
2. Open the worker dashboard.
3. View assigned tasks.
4. Open a task.
5. Update assignment progress.
6. Mark the assignment as completed.

### Safety Officer Workflow

1. Log in using an authorized safety-officer account.
2. Open the restricted safety register.
3. Review submitted safety reports.
4. Inspect report details.
5. Update report status with remarks.

Use authorized demo accounts and clearly identify any seeded traffic information as demonstration data.

---

## 🔮 Future Scope

The platform can be expanded with:

- Live integration with municipal GIS systems.
- Real-time traffic data from authorized traffic APIs.
- Mobile application for citizens and field workers.
- Push notifications for complaint status changes.
- Real-time assignment notifications.
- Advanced infrastructure analytics.
- Predictive maintenance for public infrastructure.
- Multilingual complaint submission.
- Voice-based complaint reporting.
- Integration with municipal grievance redressal systems.
- Automated service-level agreement monitoring.
- Advanced geospatial analysis and city planning insights.
- More detailed performance and resolution-time analytics.

These are potential future enhancements and are not all part of the current implementation.

---

## 👨‍💻 Team Responsibilities

**Team: DoomNdebug – Team Diamond**

| Member | Primary Responsibility |
|---|---|
| Member 1 | Citizen Portal Frontend |
| Member 2 | Official Portal Frontend and 2D Map |
| Member 3 | AI Integration and Intelligence Services |
| Member 4 | Backend, Database, API Integration, Testing and System Integration |

The team follows a modular development approach, with each member responsible for a defined part of the system and integration performed through shared API contracts.

---

## 🌟 Project Impact

The AI City Management Platform aims to improve the relationship between citizens and municipal administrations by making civic issue reporting more accessible and municipal operations more organized.

By combining AI-assisted analysis, structured complaint management, geographical visualization, and role-based workflows, the platform provides a foundation for smarter, more transparent, and more responsive city management.

**Built with the vision of making cities more connected, accountable, and intelligent.**

---

**DoomNdebug – Team Diamond**  
*AI City Management Platform | Smart Governance Through Technology*
