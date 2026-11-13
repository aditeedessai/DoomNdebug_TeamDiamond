# AI City Management Platform

## Product Requirements Document (PRD), Architecture & 6-Hour Hackathon Execution Plan

**Version:** 1.0\
**Date:** 13 November 2026\
**Project type:** GovTech / Smart Cities / Urban Infrastructure\
**Build window:** 5--6 hours\
**Team size:** 4 members\
**Delivery target:** A working, integrated MVP with two role-based
portals sharing one backend, database, AI service and city map.

------------------------------------------------------------------------

# 1. Executive Summary

The AI City Management Platform is a unified municipal operations system
that connects citizens with government departments. Citizens can report
civic problems through text, photographs or voice, track complaint
progress, view infrastructure projects, provide public feedback and
report locations with safety-related infrastructure concerns.

Government officials use a separate role-based portal to review and
manage complaints, monitor department workloads, view public feedback,
manage projects, assign field workers, inspect traffic hotspots and
identify locations with reported women's safety-related infrastructure
concerns.

Both portals use the same underlying complaint records, project data,
map data and status updates. The platform should avoid creating separate
systems for citizens and officials.

**Core product principle:** One shared municipal data platform, two
role-specific experiences.

## 1.1 Product objectives

1.  Make civic complaint registration simple and accessible.
2.  Use AI to interpret complaint text, photographs and voice
    transcripts.
3.  Route complaints to the appropriate municipal department.
4.  Give citizens transparent complaint tracking.
5.  Give officials a central view of complaints, departments, projects
    and field work.
6.  Use maps to make civic issues, traffic information and reported
    safety-related infrastructure gaps easier to understand.
7.  Turn public feedback into information officials can act upon.

## 1.2 Target users

  -----------------------------------------------------------------------
  User type               Description             Main needs
  ----------------------- ----------------------- -----------------------
  Citizen                 Resident or visitor     Report issues, track
                          using the public portal progress, view projects
                                                  and maps

  Municipal official      Authorised municipal    Review, assign,
                          employee or             prioritise and manage
                          administrator           complaints

  Department officer      Official responsible    Work through
                          for a specific          department-specific
                          department              complaints

  Field worker            Person assigned to      View assigned work and
                          inspect or resolve an   update its progress
                          issue                   
  -----------------------------------------------------------------------

For the hackathon MVP, citizen and official roles are essential.
Department officer and field worker can be represented as role variants
or demo accounts if time is limited.

------------------------------------------------------------------------

# 2. Scope and Prioritisation

A six-hour build cannot safely deliver every production-grade
capability. The team should build the complete core workflow and use
clearly labelled demo data for external information that is not
available through an API.

## 2.1 Must-have MVP

  ------------------------------------------------------------------------
  ID                Feature           Citizen portal     Officials portal
  ----------------- ----------------- ------------------ -----------------
  F01               Role-based login  Citizen            Official login
                                      login/register     

  F02               AI Snap & Speak   Submit             Review AI
                    reporting         text/photo/voice   analysis

  F03               Complaint         Track own          View, filter,
                    management and    complaints         assign and update
                    tracking                             all complaints

  F04               Government        View projects and  Create/manage
                    projects and      comment            projects and
                    feedback                             review feedback

  F05               Shared city map   View public        View complaints,
                                      complaint markers  hotspots and
                                      and available      traffic layer
                                      traffic layer      

  F06               Worker assignment View               Assign a worker
                                      progress/status    to a complaint

  F07               Women's safety    Report unsafe      View, investigate
                    reporting         locations and      and prioritise
                                      infrastructure     reported unsafe
                                      concerns           locations

  F08               Traffic hotspot   View available     Identify hotspots
                    response          traffic            and record/assign
                                      information        an officer
                                                         response
  ------------------------------------------------------------------------

## 2.2 Build if time permits

-   Speech-to-text for Hindi and English.
-   Text-to-speech confirmation.
-   Map clustering and heatmap overlay.
-   Before-and-after repair photos.
-   Notifications when complaint status changes.
-   Weather alert card.
-   Department performance charts.

## 2.3 Explicitly out of scope for this 6-hour MVP

Do not attempt these during the initial build:

-   Fully functional 3D digital twin.
-   Live city-wide CCTV or sensor integration.
-   Automatic police dispatch or emergency response.
-   Guaranteed safe-route navigation.
-   Automatic contractor payments or tender approvals.
-   Facial recognition, person tracking or individual surveillance.
-   Fully automated traffic detection without a reliable traffic data
    source.
-   Production-grade predictive flooding or crime prediction.

These require data access, validation, security controls and
substantially more development time.

------------------------------------------------------------------------

# 3. Product Structure: Two Portals, One Shared Platform

The product should have two distinct user experiences.

``` text
                  AI CITY MANAGEMENT PLATFORM
                              |
                 Shared Authentication Layer
                              |
                 Shared FastAPI Backend
                              |
          +-------------------+-------------------+
          |                   |                   |
     Citizen Portal     Officials Portal    Shared Services
          |                   |                   |
    Submit complaints   Manage complaints    AI classification
    Track complaints    Assign departments    Speech processing
    View projects       Assign field workers   Geospatial matching
    Submit feedback     Manage projects       Notifications
    View city map       Review safety reports Shared map data
    Report unsafe areas Monitor traffic
          |                   |                   |
          +-------------------+-------------------+
                              |
                   Supabase PostgreSQL
                   Supabase Storage
                   PostGIS (if enabled)
```

## 3.1 Common functionality

The following must be implemented once and reused by both portals:

-   Authentication and user identity.
-   Complaint database and complaint IDs.
-   Department records.
-   Complaint categories and priority levels.
-   City map data and location coordinates.
-   Project records and feedback.
-   Complaint status history.
-   Worker and officer assignment records.
-   AI classification service.
-   Shared API response formats.

The citizen portal should only expose information the citizen is
authorised to see. The official portal should require an authorised
role.

## 3.2 Suggested frontend routes

``` text
/
├── /login
├── /register
├── /citizen
│   ├── /dashboard
│   ├── /report
│   ├── /complaints
│   ├── /complaints/:id
│   ├── /projects
│   ├── /projects/:id
│   ├── /city-map
│   └── /safety-report
│
└── /official
    ├── /dashboard
    ├── /complaints
    ├── /complaints/:id
    ├── /departments
    ├── /projects
    ├── /feedback
    ├── /city-map
    ├── /traffic
    ├── /safety-zones
    └── /workers
```

Use a shared navigation component where appropriate, but show different
navigation items and data according to the logged-in role.

------------------------------------------------------------------------

# 4. Functional Requirements

## 4.1 F01 -- Role-Based Authentication

### Citizen requirements

-   A citizen can register and log in.
-   A citizen can access the citizen portal after authentication.
-   A citizen can view only their own private complaint details and
    submissions.
-   A citizen can view public projects and public map information.

### Official requirements

-   Officials use an official login.
-   Only accounts with an authorised official role can access the
    officials portal.
-   Officials can access complaints according to their role and
    department permissions.
-   The system must not allow a citizen to change their role by editing
    frontend data.

### MVP implementation

Use Supabase Auth.

Store role and department information in a `profiles` table. Protect
data using Supabase Row Level Security (RLS), or enforce equivalent
checks in the backend. Never trust a role supplied only by the browser.

For the demo, create pre-provisioned official accounts rather than
allowing public official registration.

**Acceptance criteria**

-   Citizen login opens the citizen portal.
-   Official login opens the officials portal.
-   A citizen cannot access official APIs by changing the URL.
-   A user cannot promote their own account to an official role.

------------------------------------------------------------------------

## 4.2 F02 -- AI-Powered Snap & Speak Complaint Registration

### Citizen workflow

1.  Open the Report a Problem page.
2.  Select or capture a photograph.
3.  Enter a description or record a voice message.
4.  Select or confirm the location on the map.
5.  Submit the report.
6.  The backend sends available text and image information to the AI
    service.
7.  AI returns a structured classification.
8.  The system checks for a matching open incident.
9.  A new complaint or linked report is saved.
10. The citizen receives a complaint/reference ID.

### Supported languages

-   English.
-   Hindi.

For the six-hour MVP, implement typed text in both languages first. Add
browser speech recognition or a speech-to-text API only if it works
reliably in the chosen demo browser.

A practical voice workflow is:

``` text
Voice recording
      |
Speech-to-text
      |
Recognised transcript
      |
AI complaint classification
      |
Citizen reviews and confirms
      |
Complaint saved
```

Do not promise direct understanding of every language or dialect unless
it has been tested.

### AI classification output

The AI service should return structured JSON:

``` json
{
  "category": "Road Infrastructure",
  "issue_type": "Pothole",
  "department": "Public Works Department",
  "severity": 8,
  "priority": "High",
  "summary": "Large pothole affecting road users",
  "recommended_action": "Inspect and repair the damaged road",
  "language": "English",
  "needs_human_review": false
}
```

Suggested departments:

  Category                             Department
  ------------------------------------ ------------------------------------
  Potholes, damaged roads, footpaths   Public Works Department
  Broken streetlights                  Electrical Department
  Garbage accumulation                 Sanitation Department
  Water leakage, drainage blockage     Water / Sewerage Department
  Traffic congestion, signal faults    Traffic / Transport Department
  Public park or facility damage       Parks / Public Assets Department
  Unsafe public infrastructure         Relevant infrastructure department

AI provides a recommendation. The official can correct the category or
department.

### Priority calculation

Use a transparent rule-based calculation rather than allowing the LLM to
determine priority without constraints.

Example:

``` text
Priority score =
  (AI severity × 10)
  + community report bonus
  + overdue bonus
```

Suggested interpretation:

-   80--100: Critical
-   60--79: High
-   35--59: Medium
-   0--34: Low

The exact thresholds and bonuses are demo configuration values and
should be tuned with municipal stakeholders before real deployment.

### Duplicate complaint handling

For the MVP:

1.  Find unresolved complaints in the same category.
2.  Compare their coordinates using PostGIS or a distance calculation.
3.  If within a configured radius, show a possible duplicate.
4.  Link the new report to the existing master incident.
5.  Increase the master incident's report count.
6.  Recalculate priority.

Start with location plus category matching. Semantic embeddings and
image similarity are optional extensions, not prerequisites.

**Acceptance criteria**

-   A citizen can submit a text complaint with a location.
-   A photograph can be uploaded and stored.
-   AI returns category, department, severity and summary.
-   The complaint is saved with a unique ID.
-   A similar nearby report can be linked to an existing incident.
-   AI failure does not silently lose the citizen's report; save it as
    unclassified/pending review.

------------------------------------------------------------------------

## 4.3 F03 -- Complaint Tracking and Management

### Citizen view

A citizen should see:

-   Complaint ID.
-   Issue summary.
-   Submission date.
-   Location.
-   Category and department.
-   Current status.
-   Latest official update.
-   Status history, where available.

Citizen-visible statuses:

``` text
Submitted
   |
Under Review
   |
Assigned
   |
In Progress
   |
Resolved
```

Also support `Rejected` or `Needs More Information` with an explanation.

### Officials view

Officials should be able to:

-   View all complaints they are authorised to manage.
-   Search by complaint ID or keyword.
-   Filter by status, department, priority and ward.
-   Open complaint details and photographs.
-   Correct AI classification.
-   Assign or reassign a department.
-   Update status and add remarks.
-   Assign a field worker.
-   Mark work as completed, subject to review.

### Acceptance criteria

-   A citizen sees their own complaint and current status.
-   An official can update a complaint.
-   The updated status is visible to the citizen.
-   Status changes are recorded with actor and timestamp.

------------------------------------------------------------------------

## 4.4 F04 -- Government Projects and Public Feedback

### Citizen requirements

A public projects page should display:

-   Project title.
-   Description.
-   Department.
-   Location.
-   Start date.
-   Expected completion date.
-   Current status.
-   Project image, if available.

A citizen can open a project and submit feedback about:

-   Construction-related inconvenience.
-   Road closures or diversions.
-   Noise or dust.
-   Damaged nearby infrastructure.
-   Accessibility concerns.
-   Other project-related problems.

### Officials requirements

Officials can:

-   Create and edit project records.
-   Change project status.
-   View feedback associated with each project.
-   Filter feedback by project and category.
-   Convert actionable feedback into a municipal complaint.

### MVP implementation

Use a `projects` table and a `project_feedback` table. Use a simple
feedback form and a management table.

For the hackathon, pre-populate two or three sample infrastructure
projects.

**Acceptance criteria**

-   Citizens can view published projects.
-   Citizens can submit feedback for a project.
-   Officials can view the submitted feedback.
-   Officials can create a complaint from actionable feedback.

------------------------------------------------------------------------

## 4.5 F05 -- Shared City Map

The city map is a shared component with role-specific layers.

### Citizen map

Display:

-   Publicly visible open complaints.
-   Publicly visible resolved complaints, if appropriate.
-   Reported infrastructure hazards.
-   Available traffic information.
-   Public project locations.
-   Reported safety-related infrastructure concerns.

Citizens should be able to select a marker and view a safe, limited
summary.

### Officials map

Display:

-   All authorised complaint locations.
-   Complaint priority and status.
-   Department filters.
-   Project locations.
-   Traffic hotspots.
-   Reported unsafe locations.
-   Worker assignments, if available.

### Map technology

Recommended for the six-hour MVP:

-   Leaflet + OpenStreetMap for a reliable 2D interactive map.
-   Marker clustering for large numbers of reports.
-   Heatmap plugin for complaint density, if time permits.
-   GeoJSON for map overlays.

A 3D map is not a core requirement for this build. MapLibre GL JS with a
3D-capable style can be explored later, but do not spend hackathon time
building a full 3D city model.

### Traffic data

Traffic must come from a real traffic provider or clearly labelled
demonstration data.

For the MVP, use a small set of seeded traffic hotspot records with
location, congestion level and timestamp. Do not present simulated
traffic as live traffic.

Possible later integrations include a traffic provider or authorised
city traffic feed.

### Map privacy

-   Do not expose citizens' phone numbers, names or private complaint
    details on public map markers.
-   Aggregate sensitive safety reports.
-   Avoid showing exact locations for reports involving personal
    harassment or vulnerable individuals.
-   Provide a separate restricted official view.

**Acceptance criteria**

-   Both portals display the same underlying map data.
-   Citizen and official map layers respect permissions.
-   Clicking a marker displays the appropriate details.
-   Filters work on the official map.
-   Demo traffic data is clearly labelled.

------------------------------------------------------------------------

## 4.6 F06 -- Traffic Hotspots and Officer Deployment

### Officials workflow

1.  View traffic hotspots on the officials map.
2.  Select a hotspot.
3.  View congestion level, location and last updated time.
4.  View the suggested response.
5.  Assign a traffic officer or response team.
6.  Record the assignment and its status.

### MVP implementation

Create a `traffic_hotspots` table with:

-   Location.
-   Congestion level.
-   Description.
-   Source.
-   Observed timestamp.
-   Status.

Create an `officer_assignments` table or reuse a general assignment
table.

The MVP should recommend deployment and allow an authorised official to
confirm the assignment. It should not autonomously dispatch police or
emergency personnel.

**Acceptance criteria**

-   Officials can view traffic hotspot markers.
-   Officials can assign an officer to a hotspot.
-   The assignment appears in the management interface.
-   The source and timestamp of traffic information are visible.

------------------------------------------------------------------------

## 4.7 F07 -- Field Worker Assignment

### Officials requirements

-   View workers or field teams.
-   Assign a worker to a complaint.
-   Set an assignment note or task.
-   View assignment status.
-   Record progress and completion remarks.

### Simplified statuses

``` text
Assigned → Accepted → In Progress → Completed
```

For the MVP, a worker can be represented by a pre-seeded record. A
separate worker mobile application is not required.

**Acceptance criteria**

-   An official can assign a worker to a complaint.
-   The assignment is stored.
-   The complaint detail shows the assigned worker.
-   The worker/task status can be updated by an authorised account.

------------------------------------------------------------------------

## 4.8 F08 -- Women's Safety: Unsafe Location Reporting and Analysis

### Product objective

Identify public locations with infrastructure-related conditions that
may create safety concerns, and help officials prioritise inspections
and maintenance.

This is an urban infrastructure feature, not a personal
emergency-response or crime-prediction system.

### Citizen requirements

A citizen can report:

-   Non-functional streetlights.
-   Poorly lit pedestrian routes.
-   Damaged or obstructed footpaths.
-   Unsafe or poorly maintained bus stops.
-   Broken public facilities.
-   A location that feels unsafe, with an optional description.

The report can include:

-   Location.
-   Issue category.
-   Description.
-   Optional photograph.
-   Optional time of observation.

Do not require a citizen to reveal their gender or personal identity to
submit a report.

### Officials requirements

Officials can:

-   View aggregated unsafe-location reports.
-   Filter by issue type and ward.
-   Identify repeated infrastructure problems.
-   See why a location has been flagged.
-   Assign an inspection or repair task.
-   Mark the issue as investigated or resolved.

### Safety-zone classification

Use evidence-based categories such as:

-   Lighting issue.
-   Pedestrian accessibility issue.
-   Public transport infrastructure issue.
-   Repeated citizen concern.
-   Unverified safety concern.

Do not label an area as criminal or dangerous solely because complaints
exist. Show the underlying evidence and report count.

### Example official view

``` text
Location: Bus stop near Ward 4
Reports: 6
Identified issues:
- 4 reports of non-functional streetlights
- 2 reports of damaged pedestrian access

Suggested action:
Electrical inspection and footpath assessment

Status: Inspection required
```

### MVP acceptance criteria

-   Citizens can submit an unsafe-location report.
-   The report is saved with coordinates and category.
-   Officials can view the report in a restricted safety dashboard.
-   Similar infrastructure reports can be grouped.
-   Officials can assign an inspection or repair task.
-   Sensitive report details are not exposed on the public map.

------------------------------------------------------------------------

# 5. Shared Architecture

## 5.1 Recommended technology stack

  -----------------------------------------------------------------------
  Layer                   Technology              Purpose
  ----------------------- ----------------------- -----------------------
  Frontend                React + Vite            Two role-based portals

  Styling                 Tailwind CSS            Responsive UI

  Routing                 React Router            Role-specific routes

  Map                     Leaflet + OpenStreetMap Shared city map

  Backend                 Python FastAPI          APIs and business logic

  Database                Supabase PostgreSQL     Shared application data

  Authentication          Supabase Auth           Citizen and official
                                                  login

  File storage            Supabase Storage        Complaint photographs

  Geospatial              PostGIS, if enabled     Location and radius
                                                  queries

  AI                      Gemini Flash API        Image/text
                                                  understanding and
                                                  classification

  Voice                   Browser Speech          Speech-to-text where
                          Recognition or speech   supported
                          API                     

  Weather (optional)      Open-Meteo              Forecast information

  Hosting (if required)   Vercel + suitable       Frontend and backend
                          FastAPI host            deployment
  -----------------------------------------------------------------------

Use one AI provider and one database during the hackathon. Avoid adding
extra model infrastructure unless the core system is already working.

## 5.2 High-level system architecture

``` text
                   CITIZEN WEB PORTAL
                           |
                           |
                   OFFICIAL WEB PORTAL
                           |
                           v
                 REACT ROUTER + AUTH
                           |
                           v
                     FASTAPI BACKEND
                           |
        +------------------+-------------------+
        |                  |                   |
        v                  v                   v
  Authentication      Complaint Service   Project Service
        |                  |                   |
        |                  v                   |
        |             AI Service               |
        |             - Classification         |
        |             - Severity               |
        |             - Department suggestion |
        |             - Summary                |
        |                  |                   |
        +------------------+-------------------+
                           |
          +----------------+------------------+
          |                |                  |
          v                v                  v
    Map Service      Assignment Service   Feedback Service
          |                |                  |
          +----------------+------------------+
                           |
                           v
                 SUPABASE POSTGRESQL
                           |
                 SUPABASE STORAGE
```

## 5.3 Backend design principle

Keep AI calls, authentication validation, complaint creation, duplicate
detection and status changes in the backend.

The frontend must not:

-   Store Gemini API keys.
-   Trust a user-supplied role.
-   Decide whether an official is authorised.
-   Directly update protected complaint records without permission
    checks.

------------------------------------------------------------------------

# 6. Database Design

Create a small schema that supports the complete workflow. Avoid
overengineering.

## 6.1 `profiles`

  Column          Type             Description
  --------------- ---------------- -------------------------------
  id              UUID             Same as Supabase Auth user ID
  full_name       TEXT             User name
  role            TEXT             citizen / official / worker
  department_id   UUID, nullable   Official's department
  created_at      TIMESTAMPTZ      Account creation time

## 6.2 `departments`

  Column        Type   Description
  ------------- ------ ---------------------------
  id            UUID   Department ID
  name          TEXT   Department name
  description   TEXT   Department responsibility

## 6.3 `complaints`

  Column               Type               Description
  -------------------- ------------------ --------------------------------
  id                   UUID               Complaint ID
  citizen_id           UUID               Submitting citizen
  title                TEXT               Complaint title
  description          TEXT               Original description
  image_url            TEXT, nullable     Uploaded photograph
  latitude             DOUBLE PRECISION   Latitude
  longitude            DOUBLE PRECISION   Longitude
  category             TEXT               AI/user-confirmed category
  issue_type           TEXT               Specific issue
  department_id        UUID, nullable     Assigned department
  severity             INTEGER            1--10
  priority             TEXT               Low/Medium/High/Critical
  status               TEXT               Complaint lifecycle
  master_incident_id   UUID, nullable     Parent incident for duplicates
  report_count         INTEGER            Number of linked reports
  safety_related       BOOLEAN            Safety infrastructure flag
  safety_category      TEXT, nullable     Type of safety concern
  ai_summary           TEXT, nullable     AI-generated summary
  created_at           TIMESTAMPTZ        Submission time
  updated_at           TIMESTAMPTZ        Last update

For a simple MVP, `master_incident_id` can reference the primary
complaint record. Keep the implementation consistent: either create a
separate incident table or use this self-reference, but do not mix both
models.

## 6.4 `complaint_updates`

  Column         Type          Description
  -------------- ------------- --------------------------------
  id             UUID          Update ID
  complaint_id   UUID          Related complaint
  actor_id       UUID          Official/worker who updated it
  status         TEXT          New status
  remarks        TEXT          Update message
  created_at     TIMESTAMPTZ   Timestamp

## 6.5 `projects`

  Column              Type               Description
  ------------------- ------------------ ---------------------------
  id                  UUID               Project ID
  title               TEXT               Project name
  description         TEXT               Project details
  department_id       UUID               Responsible department
  latitude            DOUBLE PRECISION   Project location
  longitude           DOUBLE PRECISION   Project location
  start_date          DATE               Start date
  expected_end_date   DATE               Expected completion
  status              TEXT               Planned/Ongoing/Completed
  is_published        BOOLEAN            Public visibility

## 6.6 `project_feedback`

  Column       Type          Description
  ------------ ------------- ------------------
  id           UUID          Feedback ID
  project_id   UUID          Related project
  citizen_id   UUID          Feedback author
  category     TEXT          Feedback type
  message      TEXT          Feedback content
  created_at   TIMESTAMPTZ   Submission time

## 6.7 `workers`

  Column          Type   Description
  --------------- ------ ----------------------------
  id              UUID   Worker ID
  name            TEXT   Worker/team name
  department_id   UUID   Department
  availability    TEXT   Available/Busy/Unavailable

## 6.8 `assignments`

  Column             Type             Description
  ------------------ ---------------- --------------------------------
  id                 UUID             Assignment ID
  complaint_id       UUID, nullable   Related complaint
  hotspot_id         UUID, nullable   Related traffic hotspot
  worker_id          UUID, nullable   Assigned worker
  officer_id         UUID             Assigning official
  task_description   TEXT             Assignment notes
  status             TEXT             Assigned/In Progress/Completed
  created_at         TIMESTAMPTZ      Assignment time

## 6.9 `traffic_hotspots`

  Column             Type               Description
  ------------------ ------------------ ------------------
  id                 UUID               Hotspot ID
  latitude           DOUBLE PRECISION   Location
  longitude          DOUBLE PRECISION   Location
  congestion_level   TEXT               Low/Medium/High
  source             TEXT               API or demo
  observed_at        TIMESTAMPTZ        Observation time
  description        TEXT               Context

## 6.10 Important database rules

-   Use foreign keys wherever practical.
-   Index complaint status, department ID and creation time.
-   Enable RLS for citizen-owned records and official access.
-   Restrict project creation and official assignment to authorised
    roles.
-   Do not make private complaint photographs publicly accessible by
    default.
-   Use signed URLs or controlled access for private files.
-   Validate all incoming coordinates and user input.
-   Keep safety-related personal reports restricted.

------------------------------------------------------------------------

# 7. API Contract

Agree on these contracts before parallel development. The frontend
members can build against mock responses while the backend member
implements the real endpoints.

Use `/api/v1` as the common prefix.

## 7.1 Authentication/profile

  Method   Endpoint                Purpose
  -------- ----------------------- ---------------------------
  GET      `/api/v1/me`            Get authenticated profile
  GET      `/api/v1/departments`   List departments

Authentication is performed through Supabase Auth. The frontend sends
the access token as a bearer token to FastAPI.

## 7.2 Complaints

  Method   Endpoint                            Purpose
  -------- ----------------------------------- --------------------------------------
  POST     `/api/v1/complaints`                Submit complaint and run AI analysis
  GET      `/api/v1/complaints/mine`           Citizen's complaints
  GET      `/api/v1/complaints`                Official complaint list with filters
  GET      `/api/v1/complaints/{id}`           Complaint details
  PATCH    `/api/v1/complaints/{id}`           Update allowed complaint fields
  POST     `/api/v1/complaints/{id}/updates`   Add status update
  POST     `/api/v1/complaints/{id}/assign`    Assign department/worker

Example complaint request:

``` json
{
  "description": "A large pothole near the bus stand",
  "latitude": 15.399,
  "longitude": 73.812,
  "image_url": null,
  "language": "en"
}
```

Example complaint response:

``` json
{
  "id": "demo-complaint-001",
  "category": "Road Infrastructure",
  "department": "Public Works Department",
  "severity": 8,
  "priority": "High",
  "status": "Submitted",
  "report_count": 1
}
```

## 7.3 Projects and feedback

  Method   Endpoint                           Purpose
  -------- ---------------------------------- --------------------------
  GET      `/api/v1/projects`                 List published projects
  POST     `/api/v1/projects`                 Official creates project
  PATCH    `/api/v1/projects/{id}`            Official updates project
  POST     `/api/v1/projects/{id}/feedback`   Citizen submits feedback
  GET      `/api/v1/projects/{id}/feedback`   Official views feedback

## 7.4 City map and traffic

  Method   Endpoint                         Purpose
  -------- -------------------------------- ---------------------------------
  GET      `/api/v1/map/complaints`         Map-visible complaint data
  GET      `/api/v1/map/hotspots`           Traffic hotspot data
  GET      `/api/v1/map/projects`           Project markers
  GET      `/api/v1/map/safety-zones`       Permission-filtered safety data
  POST     `/api/v1/hotspots/{id}/assign`   Assign response officer

## 7.5 Safety reporting

  -------------------------------------------------------------------------------
  Method                  Endpoint                        Purpose
  ----------------------- ------------------------------- -----------------------
  POST                    `/api/v1/safety-reports`        Submit safety
                                                          infrastructure report

  GET                     `/api/v1/safety-reports/mine`   Citizen's own reports

  GET                     `/api/v1/safety-reports`        Restricted official
                                                          list

  PATCH                   `/api/v1/safety-reports/{id}`   Official updates
                                                          investigation status
  -------------------------------------------------------------------------------

For the MVP, safety reports can also be stored in the complaints table
with `safety_related=true`. Choose one consistent implementation. Do not
build duplicate complaint and safety systems unless a separate workflow
is genuinely needed.

## 7.6 Workers and assignments

  Method   Endpoint                     Purpose
  -------- ---------------------------- -------------------------
  GET      `/api/v1/workers`            List authorised workers
  POST     `/api/v1/assignments`        Create assignment
  GET      `/api/v1/assignments`        View assignments
  PATCH    `/api/v1/assignments/{id}`   Update task status

## 7.7 Dashboard

  Method   Endpoint                          Purpose
  -------- --------------------------------- -------------------------------
  GET      `/api/v1/dashboard/summary`       Total/pending/resolved counts
  GET      `/api/v1/dashboard/departments`   Department statistics
  GET      `/api/v1/dashboard/priorities`    Priority breakdown

------------------------------------------------------------------------

# 8. AI Architecture

## 8.1 Complaint understanding pipeline

``` text
Citizen input
    |
    +-- Text description
    |
    +-- Uploaded photograph
    |
    +-- Voice recording (optional)
             |
             v
       Speech-to-text
             |
             v
     Gemini multimodal API
             |
             v
    Structured JSON response
             |
      Validate response
             |
             v
     Category + Department
     Severity + Summary
             |
             v
      Duplicate detection
             |
             v
    Priority calculation
             |
             v
       Save complaint
```

## 8.2 AI responsibilities

AI should:

-   Understand the citizen's description.
-   Interpret the uploaded image where supported.
-   Suggest a complaint category.
-   Recommend a department.
-   Generate a concise summary.
-   Suggest a severity score.
-   Detect language.

Normal backend code should:

-   Validate AI output.
-   Check duplicate locations.
-   Calculate community report counts.
-   Calculate final priority.
-   Apply access permissions.
-   Save records.
-   Trigger status updates.

Never let an LLM directly decide access permissions or perform
unrestricted database writes.

## 8.3 Suggested AI prompt

``` text
You are an assistant for a municipal complaint management system.

Analyse the citizen's complaint and return valid JSON only.

Identify:
1. Category
2. Specific issue type
3. Responsible municipal department
4. Severity from 1 to 10
5. Priority recommendation
6. A short factual summary
7. Recommended municipal action
8. Whether the complaint concerns public safety infrastructure
9. Language detected

Do not invent a location or facts that are not provided.
If information is insufficient, indicate that human review is required.

Return only the agreed JSON schema.
```

Validate the JSON using Pydantic in FastAPI.

------------------------------------------------------------------------

# 9. GitHub Repository and Team Workflow

## 9.1 Recommended repository structure

Use a monorepo to simplify integration during the hackathon.

``` text
ai-city-management/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── common/
│   │   │   ├── citizen/
│   │   │   ├── official/
│   │   │   └── map/
│   │   ├── pages/
│   │   │   ├── auth/
│   │   │   ├── citizen/
│   │   │   └── official/
│   │   ├── services/
│   │   │   ├── api.js
│   │   │   ├── complaintService.js
│   │   │   ├── projectService.js
│   │   │   └── mapService.js
│   │   ├── context/
│   │   ├── hooks/
│   │   ├── routes/
│   │   └── App.jsx
│   └── package.json
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/
│   │   │   ├── config.py
│   │   │   └── auth.py
│   │   ├── api/
│   │   │   └── routes/
│   │   │       ├── complaints.py
│   │   │       ├── projects.py
│   │   │       ├── feedback.py
│   │   │       ├── map.py
│   │   │       ├── safety.py
│   │   │       ├── workers.py
│   │   │       └── dashboard.py
│   │   ├── schemas/
│   │   ├── services/
│   │   │   ├── ai_service.py
│   │   │   ├── complaint_service.py
│   │   │   ├── duplicate_service.py
│   │   │   └── priority_service.py
│   │   └── database/
│   ├── requirements.txt
│   └── .env.example
│
├── database/
│   ├── schema.sql
│   └── seed.sql
│
├── docs/
│   ├── PRD.md
│   ├── API_CONTRACT.md
│   └── DEMO_SCRIPT.md
│
├── .gitignore
└── README.md
```

## 9.2 Branch strategy

Create these branches:

``` text
main
│
├── feature/citizen-portal
├── feature/official-portal
├── feature/ai-engine
└── feature/backend-integration
```

Each member works on their own branch. Merge into `main` only after the
integration checkpoint.

For a six-hour hackathon, avoid long-lived feature branches with large
overlapping changes. Integrate small commits frequently.

## 9.3 Four-member responsibilities

### Member 1 -- Citizen Portal Frontend

**Owns:** `frontend/src/pages/citizen/` and citizen-specific components.

Tasks:

1.  Citizen login/register screens and role-based redirect integration.
2.  Citizen dashboard.
3.  Snap & Speak complaint form.
4.  Image upload and location selection.
5.  Complaint tracking page.
6.  Projects listing and feedback form.
7.  Citizen map and unsafe-location report form.

Deliverables:

-   Working citizen portal.
-   Complaint form connected to agreed API contract.
-   Complaint tracking interface.
-   Projects and public feedback interface.

### Member 2 -- Officials Portal Frontend

**Owns:** `frontend/src/pages/official/` and official-specific
components.

Tasks:

1.  Official dashboard.
2.  Department-wise complaint list.
3.  Complaint detail and status management.
4.  Project and feedback management.
5.  Shared city map with official filters.
6.  Traffic hotspot interface.
7.  Worker assignment interface.
8.  Women's safety dashboard.

Deliverables:

-   Working official portal.
-   Complaint management UI.
-   Map and hotspot views.
-   Worker assignment and safety views.

### Member 3 -- AI and Intelligence

**Owns:** `backend/app/services/ai_service.py`, `duplicate_service.py`
and `priority_service.py`.

Tasks:

1.  Gemini integration.
2.  Structured complaint classification.
3.  English/Hindi text handling.
4.  Image understanding.
5.  Severity and department recommendation.
6.  Duplicate detection logic.
7.  Community report-based priority calculation.
8.  Optional speech-to-text integration.

Deliverables:

-   AI service with a defined input/output schema.
-   Working classification endpoint integration.
-   Duplicate matching function.
-   Fallback when AI is unavailable.

### Member 4 -- Backend, Database and Integration

**Owns:** backend API routes, database schema, authentication and
integration.

Tasks:

1.  Create Supabase project and schema.
2.  Set up authentication and role checks.
3.  Create complaint CRUD endpoints.
4.  Create project and feedback endpoints.
5.  Create map data endpoints.
6.  Create worker and traffic assignment endpoints.
7.  Integrate Member 3's AI service.
8.  Seed demo data.
9.  Verify citizen and official permissions.

Deliverables:

-   Running FastAPI backend.
-   Database tables and seed data.
-   Agreed API endpoints.
-   Shared authentication.
-   End-to-end integration.

### Shared responsibility

All members must test their own features. Member 4 coordinates
integration, but must not become the only person testing the whole
application.

------------------------------------------------------------------------

# 10. Six-Hour Execution Timeline

All four members work in parallel. The milestones below are shared
integration checkpoints.

  ----------------------------------------------------------------------------
  Time           Member 1       Member 2       Member 3         Member 4
  -------------- -------------- -------------- ---------------- --------------
  0:00--0:30     Citizen UI     Official UI    AI schema and    Repo, Supabase
                 skeleton       skeleton       prompt           schema, API
                                                                contract

  0:30--1:30     Complaint form Dashboard and  Gemini           Auth and
                 and tracking   complaint      classification   complaint
                                table                           endpoints

  1:30--2:30     Projects and   Complaint      Duplicate and    Projects,
                 feedback       management     priority logic   feedback and
                                                                complaint
                                                                integration

  2:30--3:30     Citizen map    Official map   AI integration   Map, traffic
                 and safety     and safety     and testing      and safety
                 form           dashboard                       APIs

  3:30--4:30     Connect and    Worker         Fix AI edge      Assignments
                 test citizen   assignment and cases            and dashboard
                 APIs           filters                         APIs

  4:30--5:30     Integration    Integration    End-to-end AI    End-to-end
                 fixes          fixes          tests            backend tests

  5:30--6:00     Demo           Demo           AI demo          Final merge
                 preparation    preparation    validation       and
                                                                run-through
  ----------------------------------------------------------------------------

## 10.1 First 30-minute checkpoint

Before writing extensive code, all members must agree on:

-   API endpoint names.
-   JSON field names.
-   Database table names.
-   Complaint statuses.
-   Department names.
-   Role names.
-   Map coordinate format.

The backend member should publish the schema and API contract
immediately.

## 10.2 Second checkpoint -- 2.5 hours

The team should have:

-   A citizen able to submit a complaint.
-   An official able to view the complaint.
-   AI classification working or a reliable fallback.
-   A database record created.

If this end-to-end flow does not work by this point, stop adding
features and fix the integration.

## 10.3 Third checkpoint -- 4.5 hours

The team should have:

-   Both portals connected.
-   Project feedback visible to officials.
-   Shared map data visible.
-   Department and worker assignment working.
-   Safety reports visible in the restricted officials view.

## 10.4 Final checkpoint -- 6 hours

Freeze features. Fix bugs, seed demo records and rehearse the
demonstration.

------------------------------------------------------------------------

# 11. GitHub Collaboration Rules

Use the following rules to avoid integration conflicts.

1.  Each member owns clearly defined folders.
2.  Do not edit another member's files without coordinating.
3.  Pull from `main` frequently.
4.  Commit small, working changes.
5.  Do not commit `.env`, API keys, credentials, virtual environments,
    `node_modules` or generated secrets.
6.  Maintain `.env.example` with variable names but no secret values.
7.  Use descriptive commit messages.

Suggested commits:

``` text
feat(citizen): add complaint submission form
feat(official): add complaint management dashboard
feat(ai): implement Gemini complaint classification
feat(backend): add complaint CRUD endpoints
feat(map): add complaint markers and filters
fix(auth): enforce role-based route protection
```

Suggested `.gitignore`:

``` gitignore
.env
.env.*
!.env.example

node_modules/
venv/
.venv/
__pycache__/
*.pyc

dist/
build/
.DS_Store
```

Use pull requests for merges. For the short hackathon, one designated
integration owner should merge after checking that the application still
runs.

------------------------------------------------------------------------

# 12. Frontend and Backend Integration Contract

All members should use one consistent complaint object.

``` json
{
  "id": "CMP-001",
  "title": "Large pothole near bus stand",
  "description": "The road is damaged and vehicles are struggling to pass.",
  "category": "Road Infrastructure",
  "issue_type": "Pothole",
  "department": "Public Works Department",
  "severity": 8,
  "priority": "High",
  "status": "Submitted",
  "latitude": 15.399,
  "longitude": 73.812,
  "image_url": null,
  "report_count": 3,
  "safety_related": false,
  "created_at": "2026-11-13T10:00:00Z"
}
```

For map markers, use a consistent format:

``` json
{
  "id": "CMP-001",
  "latitude": 15.399,
  "longitude": 73.812,
  "type": "complaint",
  "category": "Road Infrastructure",
  "priority": "High",
  "status": "Submitted"
}
```

Use ISO 8601 timestamps in UTC. Convert them to the user's local
timezone in the frontend.

------------------------------------------------------------------------

# 13. UI/UX Recommendations

## Citizen portal

Suggested navigation:

``` text
Home | Report a Problem | My Complaints | City Map | Projects
```

The homepage should prioritise:

-   A prominent Report a Problem action.
-   Recent complaint updates.
-   Nearby public projects.
-   A city map preview.
-   An easy-to-find unsafe-location reporting option.

Keep the complaint form short. Use a step-by-step flow if needed.

## Officials portal

Suggested navigation:

``` text
Dashboard | Complaints | Departments | City Map
Projects & Feedback | Traffic | Women's Safety | Workers
```

Dashboard cards:

-   Total complaints.
-   Pending complaints.
-   High-priority complaints.
-   Resolved complaints.
-   Department backlog.
-   Traffic hotspots.

Below the cards:

-   Complaint trend or department chart.
-   Recent complaints table.
-   City map preview.
-   Safety infrastructure alerts.
-   Work assignments.

Do not build two completely different map systems. Reuse one map
component with role-specific layers and access rules.

------------------------------------------------------------------------

# 14. Testing and Acceptance Checklist

## Authentication

-   [ ] Citizen can register and log in.
-   [ ] Official can log in.
-   [ ] Role-based redirect works.
-   [ ] Citizen cannot access official operations.
-   [ ] Protected API endpoints validate the token and role.

## Complaint registration

-   [ ] Citizen can submit a text complaint.
-   [ ] Photograph upload works.
-   [ ] Location is saved correctly.
-   [ ] AI classification returns valid output.
-   [ ] AI failure has a fallback.
-   [ ] Complaint ID is generated.

## Duplicate detection

-   [ ] A nearby same-category complaint is detected as a possible
    duplicate.
-   [ ] Report count increases when a report is linked.
-   [ ] Unrelated complaints are not automatically merged.
-   [ ] Officials can review questionable matches.

## Tracking and management

-   [ ] Citizen sees their own complaints.
-   [ ] Official sees authorised complaints.
-   [ ] Official can update status.
-   [ ] Citizen sees updated status.
-   [ ] Update history records the change.

## Projects and feedback

-   [ ] Citizen can view published projects.
-   [ ] Citizen can submit project feedback.
-   [ ] Official can view feedback.
-   [ ] Official can update project status.

## Map

-   [ ] Complaint markers appear.
-   [ ] Project markers appear.
-   [ ] Traffic data has a visible source/timestamp.
-   [ ] Citizen and official layers respect permissions.
-   [ ] Sensitive reports are not exposed publicly.

## Traffic and workers

-   [ ] Official can view a hotspot.
-   [ ] Official can assign an officer or response team.
-   [ ] Official can assign a field worker to a complaint.
-   [ ] Assignment status is visible.

## Women's safety

-   [ ] Citizen can submit an unsafe-location report.
-   [ ] The report is categorised correctly.
-   [ ] Officials can see restricted safety reports.
-   [ ] Officials can assign inspection/repair work.
-   [ ] Sensitive personal details are not shown on public maps.

------------------------------------------------------------------------

# 15. Demo Scenario

Use one connected story to demonstrate both portals.

## Scenario A -- Road infrastructure complaint

1.  Log in as a citizen.
2.  Upload a photograph of a pothole.
3.  Enter: "There is a large pothole near the bus stand."
4.  Submit the complaint.
5.  Show AI category, department and severity.
6.  Submit another report with the same nearby location.
7.  Show that it is linked to the existing incident.
8.  Log in as an official.
9.  Show the complaint on the dashboard and map.
10. Assign it to the Public Works Department and a field worker.
11. Update the complaint to In Progress.
12. Return to the citizen portal and show the updated status.

## Scenario B -- Project feedback

1.  Citizen opens an ongoing road construction project.
2.  Citizen reports that construction is blocking pedestrian access.
3.  Official opens the project feedback page.
4.  Official reviews the feedback.
5.  Official converts the issue into a complaint or assigns an
    inspection.

## Scenario C -- Women's infrastructure safety

1.  Citizen reports non-functional streetlights near a bus stop.
2.  The report appears in the restricted safety dashboard.
3.  Officials see similar reports around that location.
4.  The map highlights the infrastructure concern.
5.  An inspection or electrical repair task is assigned.

## Scenario D -- Traffic hotspot

1.  Display a seeded high-congestion hotspot.
2.  Official opens the hotspot.
3.  The system shows the source and timestamp.
4.  Official assigns a traffic officer or response team.
5.  The assignment appears in the operations dashboard.

------------------------------------------------------------------------

# 16. Risks and Mitigation

  -----------------------------------------------------------------------
  Risk                                Mitigation
  ----------------------------------- -----------------------------------
  Gemini API unavailable or slow      Provide a deterministic mock
                                      classification fallback

  Voice recognition unavailable in    Allow typed English/Hindi input
  browser                             

  Image upload fails                  Allow text-only complaints

  Supabase RLS configuration delays   Test permissions early; never leave
                                      production data open

  Map provider unavailable            Use seeded GeoJSON or fallback
                                      markers

  No live traffic API                 Clearly label sample hotspot data

  Duplicate detection merges wrong    Use conservative matching and
  issues                              official review

  Team integration conflicts          Agree on contracts and folder
                                      ownership in first 30 minutes

  Six-hour time limit                 Prioritise complete end-to-end
                                      workflows over extra features

  Sensitive safety reports exposed    Use restricted access and
                                      aggregated public map data
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 17. Definition of Done

The hackathon MVP is considered complete when:

1.  A citizen can log in and submit a complaint.
2.  The complaint can include a photograph and location.
3.  AI can classify the complaint or a clear fallback can handle it.
4.  The complaint is stored in the shared database.
5.  An authorised official can view and manage it.
6.  An official can assign a department and worker.
7.  The citizen can track status updates.
8.  Citizens can view projects and submit feedback.
9.  Officials can review that feedback.
10. Both portals display shared map data with appropriate permissions.
11. Citizens can report unsafe infrastructure locations.
12. Officials can review and assign actions for those reports.
13. Traffic hotspots can be displayed and assigned to a response officer
    using real or clearly labelled demo data.

The 3D map, live traffic feeds, advanced prediction and full speech
automation are not required for the MVP to be considered complete.

------------------------------------------------------------------------

# 18. Final Build Strategy

The team's most important deliverable is not the number of pages. It is
the connected municipal workflow.

**Build in this order:**

1.  Authentication and shared database.
2.  Citizen complaint submission.
3.  AI classification and backend storage.
4.  Officials complaint dashboard.
5.  Complaint assignment and status tracking.
6.  Projects and public feedback.
7.  Shared city map.
8.  Traffic and worker assignment.
9.  Women's safety reporting and restricted official view.
10. Final integration and demo.

**Do not let individual members finish isolated pages without connecting
them.** A simple working flow across both portals is more valuable than
a visually impressive but disconnected collection of screens.

## Final product positioning

> **An AI-powered City Management Platform that transforms citizen
> reports and public feedback into actionable municipal intelligence,
> helping government officials coordinate departments, manage
> infrastructure, respond to traffic concerns and create safer public
> spaces.**

**Core architecture:** Two role-based portals + one shared backend + one
database + one AI intelligence layer + one shared geospatial service.

**Hackathon strategy:** Build the complete complaint-to-resolution
workflow first, then layer projects, maps, traffic and women's
infrastructure safety onto the same system.
