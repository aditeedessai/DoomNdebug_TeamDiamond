# DoomNdebug Team Diamond — Team Allocation & Execution Plan
## AI City Management Platform | 4 Members | 5–6 Hour Hackathon

**Purpose:** This document converts the project PRD into a conflict-minimising task plan. It defines exactly who owns each task and file area, what must be completed first, what depends on another member, and how the four members should integrate their work.

**Source:** Based on `AI_City_Management_Platform_PRD.md` supplied by the team.

---

# 1. Team structure and ownership

| Member | Role | Primary responsibility | Owns these areas |
|---|---|---|---|
| **Member 1** | Citizen Portal Developer | Citizen-facing pages and citizen workflows | `frontend/src/pages/citizen/`, `frontend/src/components/citizen/`, `frontend/src/services/citizenService.js` |
| **Member 2** | Officials Portal Developer | Municipal dashboard and official workflows | `frontend/src/pages/official/`, `frontend/src/components/official/`, `frontend/src/services/officialService.js` |
| **Member 3** | AI & Intelligence Developer | Complaint understanding, classification, duplicate matching and priority | `backend/app/services/ai_service.py`, `duplicate_service.py`, `priority_service.py`, `backend/app/schemas/ai.py` |
| **Member 4** | Backend, Database & Integration Lead | API, authentication, database, shared services and integration | `backend/app/api/`, `backend/app/core/`, `backend/app/database/`, `backend/app/schemas/` (except `ai.py`), `database/`, backend entry point |

**Integration coordinator:** Member 4 coordinates integration and final verification. This does not mean Member 4 should write everyone else's modules. Each member remains responsible for making their own module work against the agreed contracts.

## Non-negotiable ownership rule

- A member edits only their assigned folders/files.
- If a change is needed in another member's area, request it from that owner instead of editing the file directly.
- Shared files have exactly one owner.
- Do not rename folders, routes, database fields or API response properties without informing all members.
- Do not let two members independently create the same component, endpoint, table or service.

---

# 2. Repository structure and file ownership

Use this structure as the agreed target. If the repository already contains a different structure, adapt the paths once as a team before coding; do not create competing structures.

```text
DoomNdebug_TeamDiamond/
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── common/              # Member 1 creates base; then shared/read-only
│   │   │   ├── citizen/             # Member 1
│   │   │   ├── official/            # Member 2
│   │   │   └── map/                 # Member 2 owns shared map component
│   │   ├── pages/
│   │   │   ├── citizen/             # Member 1
│   │   │   └── official/            # Member 2
│   │   ├── services/
│   │   │   ├── api.js               # Member 1 creates once; shared/read-only
│   │   │   ├── citizenService.js    # Member 1
│   │   │   └── officialService.js   # Member 2
│   │   ├── context/                 # Member 1 creates auth context; shared/read-only
│   │   ├── routes/                  # Member 1 creates route shell; shared/read-only
│   │   ├── App.jsx                  # Member 1 owns; others request changes
│   │   └── main.jsx                 # Member 1 owns
│   └── package.json                 # Member 1 owns; others request dependencies
│
├── backend/
│   ├── app/
│   │   ├── main.py                  # Member 4
│   │   ├── core/                    # Member 4
│   │   ├── api/routes/              # Member 4
│   │   ├── schemas/
│   │   │   ├── ai.py                # Member 3
│   │   │   └── other schemas        # Member 4
│   │   ├── services/
│   │   │   ├── ai_service.py        # Member 3
│   │   │   ├── duplicate_service.py # Member 3
│   │   │   ├── priority_service.py  # Member 3
│   │   │   └── other services       # Member 4
│   │   └── database/                # Member 4
│   ├── requirements.txt             # Member 4 owns; Member 3 requests packages
│   └── .env.example                 # Member 4
│
├── database/
│   ├── schema.sql                   # Member 4
│   └── seed.sql                     # Member 4
│
├── docs/
│   └── PRD.md                       # Existing PRD; read-only during build
│
├── .gitignore                       # One owner: Member 4
└── README.md                        # One owner: Member 4
```

### Shared-file owners

| Shared file/resource | Sole owner | Rule for other members |
|---|---|---|
| `frontend/package.json` | Member 1 | Request packages; do not edit directly |
| `frontend/src/App.jsx` and `main.jsx` | Member 1 | Request route or shell changes |
| `frontend/src/routes/` | Member 1 | Member 2 supplies required route names |
| `frontend/src/context/` | Member 1 | Other members consume the agreed auth hook/context |
| `frontend/src/services/api.js` | Member 1 | Do not create another API client |
| `frontend/src/components/map/` | Member 2 | Member 1 consumes the exported map component |
| `backend/requirements.txt` | Member 4 | Member 3 sends required package names to Member 4 |
| `backend/app/main.py` | Member 4 | Other members do not edit app registration |
| `backend/app/schemas/ai.py` | Member 3 | Member 4 imports it; do not duplicate AI schemas |
| `database/schema.sql`, `seed.sql` | Member 4 | Other members request schema changes |
| `.gitignore`, `README.md` | Member 4 | No parallel edits |

**Important:** The PRD proposes a shared map. Member 2 owns the reusable map component and its official map usage; Member 1 imports that component in the citizen portal. If the component needs a different interface, agree on it before either portal integrates it.

---

# 3. Numbered task allocation

Task IDs are used for stand-ups, commits and handovers. Complete tasks in dependency order, not simply in numerical order.

## Member 1 — Citizen Portal Frontend

**Goal:** A citizen can log in, submit a civic complaint, view its progress, see public projects, submit feedback, view the city map and report an unsafe infrastructure location.

| Task ID | Task | Detailed work / expected result | Depends on | Priority |
|---|---|---|---|---|
| **M1-01** | Set up frontend shell | Initialise React + Vite in `frontend/`; install agreed frontend packages; create basic app entry point | None | Must |
| **M1-02** | Shared frontend foundation | Create `App.jsx`, route shell, common layout, `api.js` and auth context. Publish component/API usage instructions to Member 2 | M1-01 | Must |
| **M1-03** | Citizen login/register UI | Build citizen login/register screens and role-aware redirect using the agreed auth interface | M1-02, M4-02 | Must |
| **M1-04** | Citizen dashboard | Show report action, recent complaints and project/map previews | M1-02 | Must |
| **M1-05** | Snap & Speak complaint form | Text description, English/Hindi text input, photo selection, location input/map selection and submit action. Voice capture/transcription is optional | M1-02, M3-01, M4-03 | Must |
| **M1-06** | Complaint tracking | List citizen's own complaints; show complaint ID, category, department, priority, status and latest update | M1-02, M4-04 | Must |
| **M1-07** | Projects and feedback | Display published projects and submit project-related feedback | M1-02, M4-05 | Must |
| **M1-08** | Citizen city map | Use Member 2's shared map component; show only public/permission-filtered complaint, project and safety markers | M2-06, M4-06 | Must |
| **M1-09** | Unsafe-location report form | Report poor lighting, damaged footpaths, unsafe bus-stop infrastructure or other infrastructure concerns with location and optional image | M1-02, M4-07 | Must |
| **M1-10** | Citizen flow testing | Test login, submit complaint, tracking, project feedback, map and safety report; report bugs with reproduction steps | M1-03 to M1-09 | Must |

**Member 1 must not edit:** official pages, AI service files, FastAPI routes, database schema, `main.py`, or the shared map component.

**Deliverable:** Citizen portal that can use the agreed API contract. If an endpoint is not ready, use a clearly isolated temporary mock in the citizen service layer; do not hardcode mock data throughout page components.

## Member 2 — Government Officials Portal Frontend

**Goal:** An authorised official can view municipal operations, filter complaints, update complaint status, review project feedback, inspect map hotspots, assign workers/officers and review safety reports.

| Task ID | Task | Detailed work / expected result | Depends on | Priority |
|---|---|---|---|---|
| **M2-01** | Officials portal layout | Create official portal layout, sidebar/navigation and page shell inside `pages/official/` and `components/official/` | M1-02 | Must |
| **M2-02** | Officials dashboard | Summary cards for total, pending, high-priority and resolved complaints; department breakdown and recent complaints | M4-08 | Must |
| **M2-03** | Complaint management | Table/list with search and filters for status, department, priority and ward; detail view with AI classification | M4-04 | Must |
| **M2-04** | Complaint actions | UI to correct department/category, update status and add official remarks | M2-03, M4-04 | Must |
| **M2-05** | Projects and feedback management | View project feedback, filter by project and show action/convert-to-complaint control if endpoint is available | M4-05 | Must |
| **M2-06** | Shared city map component | Build reusable Leaflet map in `components/map/`; support markers, marker selection, layers and role-specific props. Keep it 2D for MVP | M1-02 | Must |
| **M2-07** | Official map and traffic hotspots | Use shared map with official filters; show traffic markers with source and timestamp, using labelled demo data if needed | M2-06, M4-06 | Must |
| **M2-08** | Worker assignment UI | Select a worker/team, assign to a complaint, show assignment status | M4-09 | Must |
| **M2-09** | Women's safety dashboard | Restricted official view of safety reports; show issue type, ward/location, report count, reason/evidence and inspection status | M4-07 | Must |
| **M2-10** | Officer/hotspot assignment UI | Select hotspot and record an officer/response-team assignment; no automatic dispatch | M4-06 | Should |
| **M2-11** | Officials flow testing | Test filters, complaint updates, feedback, map, traffic, assignments and restricted safety view | M2-02 to M2-10 | Must |

**Member 2 must not edit:** citizen pages, `App.jsx`, `main.jsx`, route definitions, API client, backend routes, AI service files or SQL schema. Send any shared-shell changes to Member 1.

**Deliverable:** Officials portal with the agreed route names and API service calls. The shared map component must export a documented interface for Member 1.

## Member 3 — AI & Intelligence

**Goal:** Convert citizen text and optional images into a validated structured complaint analysis; support conservative duplicate matching and transparent priority calculation.

| Task ID | Task | Detailed work / expected result | Depends on | Priority |
|---|---|---|---|---|
| **M3-01** | Agree AI input/output contract | Agree request fields and response JSON with Member 4; define Pydantic schema in `schemas/ai.py` | Initial team contract | Must |
| **M3-02** | Gemini service setup | Implement Gemini client in `services/ai_service.py`; read API key from environment; set timeout and handle provider errors | M3-01, M4-01 | Must |
| **M3-03** | Complaint classification | Classify text into category, issue type, department, severity, summary, recommended action and detected language | M3-02 | Must |
| **M3-04** | English/Hindi handling | Accept English and Hindi descriptions; return a consistent language field and structured output | M3-03 | Must |
| **M3-05** | Image understanding | If time permits, pass uploaded image or accessible image URL to the supported multimodal model and include visual evidence in analysis | M3-03, M4-03 | Should |
| **M3-06** | AI fallback and validation | Validate model output; handle malformed JSON, timeout, missing key or API failure. Return a safe `needs_human_review` result rather than losing the complaint | M3-02, M3-03 | Must |
| **M3-07** | Duplicate matching | Implement conservative same-category + nearby-coordinate matching in `duplicate_service.py`; return a possible match rather than merging uncertain reports automatically | M4-01, M4-03 | Must |
| **M3-08** | Priority calculation | Implement deterministic severity + community-count/overdue bonus in `priority_service.py`; document thresholds | M3-01, M3-07 | Must |
| **M3-09** | Integration handover | Give Member 4 exact import names, function signatures, environment variable names and sample input/output | M3-02 to M3-08 | Must |
| **M3-10** | AI tests | Test English, Hindi, ambiguous complaint, invalid response, duplicate and AI-unavailable cases | M3-03 to M3-09 | Must |
| **M3-11** | Optional speech-to-text support | Investigate browser/API speech-to-text only after typed English/Hindi complaint analysis works | M3-10 | Optional |

**Member 3 must not edit:** API route files, `main.py`, database schema, `requirements.txt`, frontend files or Member 4's complaint CRUD service. Send package requirements to Member 4.

**Deliverable:** Importable AI/duplicate/priority service functions with a documented contract and fallback. Member 3 does not independently create a second FastAPI application or a competing complaint endpoint.

## Member 4 — Backend, Database & Integration Lead

**Goal:** Provide one secure FastAPI backend, one shared Supabase schema, agreed API contracts and end-to-end integration for both portals and AI services.

| Task ID | Task | Detailed work / expected result | Depends on | Priority |
|---|---|---|---|---|
| **M4-01** | Backend skeleton and configuration | Create FastAPI app structure, configuration loader, CORS, health endpoint and environment example | None | Must |
| **M4-02** | Supabase schema and authentication | Create tables, relationships, profile roles, JWT validation approach and role/department checks. Prepare citizen and official demo accounts | M4-01 | Must |
| **M4-03** | Complaint CRUD and upload | Implement complaint create/list/detail/update endpoints; integrate storage or accept image URL; validate location and ownership | M4-02 | Must |
| **M4-04** | Complaint lifecycle and status history | Implement status updates, official remarks, department assignment and update history; call Member 3 AI/priority/duplicate services | M3-09, M4-03 | Must |
| **M4-05** | Projects and feedback APIs | Implement published project list, official create/update, citizen feedback submission and official feedback retrieval | M4-02 | Must |
| **M4-06** | Map and traffic APIs | Return permission-filtered complaint/project/safety map data; create and list clearly labelled demo traffic hotspots | M4-03, M4-05 | Must |
| **M4-07** | Safety report handling | Store safety-related infrastructure reports, restrict official access, provide citizen-owned report access and official investigation status | M4-02, M4-03 | Must |
| **M4-08** | Dashboard APIs | Return summary counts, department statistics and priority breakdown | M4-03, M4-04 | Must |
| **M4-09** | Worker and officer assignments | Seed demo workers; implement complaint-worker and hotspot-officer assignment and status endpoints | M4-02, M4-04, M4-06 | Must |
| **M4-10** | Seed data and API documentation | Add departments, sample projects, workers, complaints and traffic hotspots; publish actual endpoint request/response examples | M4-02 to M4-09 | Must |
| **M4-11** | Integration and permissions testing | Test frontend flows against real APIs; verify role permissions, RLS/backend checks and error handling | M1/M2/M3 handovers | Must |
| **M4-12** | Final merge and demo readiness | Merge approved branches, resolve integration issues, check environment setup and run the end-to-end demo | All members | Must |

**Member 4 must not edit:** citizen or official page/component files, except a small integration fix explicitly agreed with the owner. Member 4 owns backend and database integration, not all frontend implementation.

**Deliverable:** Running FastAPI service, Supabase schema and seed data, documented API contract, secure role checks and a working integrated application.

---

# 4. Dependency order — who needs to finish what first?

This is the most important section. Follow the sequence so nobody builds against a changing contract.

| Order | Task(s) | Owner | Must be handed over before | Handover to |
|---|---|---|---|---|
| **D01** | Agree repository structure, roles, departments, complaint statuses and API field names | All; Member 4 records decisions | Any major coding | All |
| **D02** | Create frontend shell, shared routes, API client and auth interface | Member 1 | Citizen/official page integration | Members 2 and 4 |
| **D03** | Create backend skeleton, environment config and health endpoint | Member 4 | API implementation | Members 1, 2 and 3 |
| **D04** | Publish database schema and API contract | Member 4 | Real API integration | Members 1, 2 and 3 |
| **D05** | Publish AI input/output schema and function signatures | Member 3 | AI integration in complaint endpoint | Member 4 |
| **D06** | Complete complaint creation API with fallback classification | Members 3 and 4 | End-to-end complaint demo | Member 1 |
| **D07** | Complete citizen complaint form and tracking UI | Member 1 | Citizen-to-official flow | Member 4 |
| **D08** | Complete officials complaint list/detail/status UI | Member 2 | Official complaint management demo | Member 4 |
| **D09** | Complete project/feedback APIs and both portal screens | Members 1, 2 and 4 | Project feedback demo | All |
| **D10** | Complete shared map component and map endpoints | Members 2 and 4 | Both map screens | Member 1 consumes component |
| **D11** | Complete safety report API and restricted officials view | Members 1, 2 and 4 | Safety demo | All |
| **D12** | Complete worker/hotspot assignments and dashboard summary | Members 2 and 4 | Officials operations demo | All |
| **D13** | Full end-to-end test, bug fixing and final demo | All; Member 4 coordinates | Final submission | All |

## Critical dependency rule

**The API contract and database field names must be frozen early.** Frontend members can use temporary mock responses while backend endpoints are being developed, but the mock response must match the agreed API response exactly. Do not let the frontend invent its own field names.

---

# 5. Six-hour execution schedule

All four members work in parallel. Checkpoints are deadlines for working handovers, not a reason to wait idle.

| Time | Member 1 — Citizen | Member 2 — Officials | Member 3 — AI | Member 4 — Backend |
|---|---|---|---|---|
| **0:00–0:20** | Review routes and citizen workflow | Review official workflow and map needs | Agree AI schema and prompt | Create backend skeleton; publish schema/API contract |
| **0:20–1:00** | Build citizen layout and complaint form UI using mock data | Build official layout and complaint table using mock data | Implement Gemini classification and fallback | Create Supabase tables, auth checks and complaint endpoint |
| **1:00–2:00** | Connect complaint submission and tracking | Connect complaint list/detail/status UI | Complete classification, validation and priority logic | Integrate AI into complaint creation; test citizen-to-official flow |
| **2:00–3:00** | Build projects/feedback and safety report forms | Build project feedback management and dashboard | Complete duplicate matching; support image input if stable | Build project/feedback and safety APIs |
| **3:00–4:00** | Integrate citizen map using shared map component | Build shared Leaflet map, official layers and traffic UI | Test AI edge cases; assist integration if AI is stable | Build map, traffic, worker and assignment APIs |
| **4:00–5:00** | Test citizen workflows and fix owned files | Test official workflows and fix owned files | Test end-to-end AI and fix owned service files | Connect remaining APIs; verify permissions and seed data |
| **5:00–5:30** | Fix bugs; prepare citizen demo | Fix bugs; prepare officials demo | Verify AI demo and fallback | Merge approved branches; run integrated app |
| **5:30–6:00** | Demo rehearsal | Demo rehearsal | Demo rehearsal | Final smoke test and backup demo data |

## Checkpoint gates

| Checkpoint | Required working result | If not achieved |
|---|---|---|
| **C1 — 0:20** | Shared contract, frontend shell, backend skeleton and AI schema agreed | Stop adding features; finish interfaces first |
| **C2 — 2:00** | Citizen submits complaint; backend saves it; official can see it; AI works or fallback works | Stop optional features and fix the core flow |
| **C3 — 4:00** | Projects/feedback and safety reporting are connected; map data is available | Use simple list/map markers and seeded data |
| **C4 — 5:00** | Worker/hotspot assignments and role checks work; both portals use real APIs | Defer optional voice, heatmap and visual polish |
| **C5 — 5:30** | All approved changes integrated; no new features | Freeze features and only fix blockers |

---

# 6. GitHub workflow to minimise merge conflicts

## 6.1 One branch per member

Create these branches from `main`:

| Member | Branch |
|---|---|
| Member 1 | `feature/citizen-portal` |
| Member 2 | `feature/official-portal` |
| Member 3 | `feature/ai-engine` |
| Member 4 | `feature/backend-integration` |

Each member should clone the repository once, then switch to their own branch.

```bash
git clone https://github.com/YOUR_USERNAME/DoomNdebug_TeamDiamond.git
cd DoomNdebug_TeamDiamond
git checkout -b feature/your-branch-name
```

Replace the branch name with the one assigned to that member.

## 6.2 Daily work commands

Before beginning work on your own branch:

```bash
git status
git pull origin main
```

If your branch has already been created and tracks the remote, update it with:

```bash
git pull
```

To save and push your work:

```bash
git add <your-owned-files>
git commit -m "feat: describe your task"
git push -u origin feature/your-branch-name
```

For later pushes:

```bash
git add <your-owned-files>
git commit -m "fix: describe your fix"
git push
```

**Prefer `git add <your-owned-files>` over `git add .`** so you do not accidentally commit another member's files, `.env`, virtual environments or generated files.

## 6.3 Pull Request sequence

Use this merge order:

| Merge order | Branch | Why this order |
|---|---|---|
| **1** | `feature/backend-integration` | Provides database, API and backend foundation |
| **2** | `feature/ai-engine` | Adds AI service files consumed by backend |
| **3** | `feature/citizen-portal` | Adds citizen UI and shared frontend shell |
| **4** | `feature/official-portal` | Adds official UI and shared map component |

Member 4 should review and merge each PR into `main`. The branch owner should update their branch from the latest `main` before opening or updating the PR. Coordinate this with Member 4 so two people do not merge simultaneously.

**Important:** If a branch was created before another branch is merged, it may not contain the latest files. Before its PR is merged, update it from `main` and test again.

Example:

```bash
git checkout feature/official-portal
git fetch origin
git merge origin/main
```

Resolve any conflicts only in files you own. If a conflict appears in another member's owned file, ask that owner to resolve it with you. Do not blindly accept "ours" or "theirs".

## 6.4 Rules that prevent most conflicts

1. Do not let all members edit `App.jsx`, `main.jsx`, `package.json` or shared config.
2. Do not let more than one member edit `requirements.txt`, SQL schema or API route registration.
3. Member 1 owns the frontend shell and API client.
4. Member 2 owns the shared map component.
5. Member 3 owns only AI-related service/schema files.
6. Member 4 owns backend routes, database and integration.
7. Use separate service files for citizen and official API calls.
8. Agree on API field names once; do not rename them independently.
9. Commit small changes frequently; do not wait until the end to push everything.
10. Do not commit `.env`, API keys, credentials, `node_modules/`, `.venv/` or `venv/`.
11. Do not rename or move another member's files.
12. Do not merge an untested branch just to meet a checkpoint.

## 6.5 If a merge conflict happens

1. Stop editing the conflicted file.
2. Identify who owns that file using Section 2.
3. Contact the owner and compare both changes.
4. Keep the required functionality from both changes.
5. Run the relevant frontend/backend test.
6. Commit the conflict resolution and push the updated branch.

Do not delete the file or accept one side without reviewing the content.

---

# 7. Shared contracts to agree before coding

Member 4 records the final choices and sends them to the team. Members 1, 2 and 3 use the same names.

| Contract item | Agreed value / example |
|---|---|
| Frontend | React + Vite |
| Backend | Python FastAPI |
| Database | Supabase PostgreSQL |
| Authentication | Supabase Auth |
| AI provider | Gemini API |
| Map | Leaflet + OpenStreetMap |
| API prefix | `/api/v1` |
| Roles | `citizen`, `official`, `worker` |
| Complaint statuses | `Submitted`, `Under Review`, `Assigned`, `In Progress`, `Resolved`, `Rejected`, `Needs More Information` |
| Priority levels | `Low`, `Medium`, `High`, `Critical` |
| Coordinates | `latitude`, `longitude` as numeric values |
| Timestamps | ISO 8601 |
| Department examples | Public Works, Electrical, Sanitation, Water/Sewerage, Traffic/Transport, Parks/Public Assets |

### Standard complaint response

All members should use the same shape:

```json
{
  "id": "CMP-001",
  "title": "Large pothole near bus stand",
  "description": "The road is damaged.",
  "category": "Road Infrastructure",
  "issue_type": "Pothole",
  "department": "Public Works Department",
  "severity": 8,
  "priority": "High",
  "status": "Submitted",
  "latitude": 15.399,
  "longitude": 73.812,
  "image_url": null,
  "report_count": 1,
  "safety_related": false,
  "created_at": "2026-11-13T10:00:00Z"
}
```

### AI service handover

Member 3 must give Member 4:

- Exact Python import path.
- Exact function name and parameters.
- Exact response schema.
- Required environment variable names.
- Required package names.
- Example successful response.
- Example fallback response.
- Whether image input expects a file, bytes or URL.

Member 4 must not guess these signatures or create a duplicate AI implementation.

### Frontend handover

Member 1 must give Member 2:

- The route registration process.
- The shared layout and auth context usage.
- The API client import path.
- The agreed navigation/component conventions.

Member 2 must give Member 1:

- The map component export name.
- Its props, such as markers, layers and click handler.
- The marker object shape.
- How to hide restricted layers in citizen mode.

---

# 8. MVP priority — what to cut if time runs short

The PRD identifies several features as optional or out of scope. Protect the complete citizen-to-official complaint workflow first.

| Priority | Feature | Build decision |
|---|---|---|
| **P0 — Essential** | Citizen and official login/role separation | Build |
| **P0 — Essential** | Text complaint submission with location | Build |
| **P0 — Essential** | AI classification or safe fallback | Build |
| **P0 — Essential** | Complaint saved and visible to officials | Build |
| **P0 — Essential** | Official status update and citizen tracking | Build |
| **P0 — Essential** | Department assignment | Build |
| **P1 — Important** | Projects and citizen feedback | Build simple version |
| **P1 — Important** | Safety infrastructure reporting and restricted official view | Build simple version |
| **P1 — Important** | Shared 2D city map and complaint/project markers | Build simple version |
| **P1 — Important** | Worker assignment | Build simple version |
| **P2 — If time permits** | Traffic hotspot assignment | Use seeded, clearly labelled demo data |
| **P2 — If time permits** | Photo-based AI understanding | Add after text classification works |
| **P2 — If time permits** | Hindi/English browser voice input | Add only if reliable in demo browser |
| **P2 — If time permits** | Heatmap and marker clustering | Add after basic map works |
| **Defer** | Full 3D city digital twin, live CCTV/sensors, automatic police dispatch, guaranteed safe routing, predictive crime/flooding | Do not build in this hackathon window |

**Safety note:** Do not label an area as criminal or dangerous based only on citizen reports. Show the infrastructure issue, number of reports and evidence. Keep sensitive safety reports restricted and avoid exposing exact personal-report locations on the public map.

---

# 9. Definition of done by member

| Member | Required handover before integration |
|---|---|
| **Member 1** | Citizen pages render; form validation works; citizen API calls use the shared API client; complaint tracking displays API data; no edits to official/backend-owned files |
| **Member 2** | Official pages render; filters and actions work; shared map component is reusable; map layers respect role; no edits to citizen shell/backend-owned files |
| **Member 3** | AI functions import successfully; output validates against schema; duplicate matching is conservative; priority calculation is deterministic; fallback works without Gemini |
| **Member 4** | FastAPI starts; database schema and seed data run; API contract is published; auth/role checks work; frontend APIs are integrated; end-to-end workflow passes |

## Final end-to-end demo flow

1. Citizen logs in.
2. Citizen submits a pothole complaint with a location and optional photograph.
3. AI suggests category, department, severity and summary; citizen receives a complaint ID.
4. Official logs in and sees the complaint in the dashboard.
5. Official reviews the AI suggestion, confirms department and assigns a worker.
6. Official updates status to `In Progress`.
7. Citizen opens complaint tracking and sees the updated status.
8. Citizen submits feedback on an ongoing public project; official sees it.
9. Citizen reports a non-functional streetlight; the report appears in the restricted safety view.
10. Official views a seeded traffic hotspot and records a response assignment.

---

# 10. Team working agreement

Before starting, fill in the actual names and GitHub usernames:

| Role | Member name | GitHub username | Branch |
|---|---|---|---|
| Citizen Portal | __________________ | __________________ | `feature/citizen-portal` |
| Officials Portal | __________________ | __________________ | `feature/official-portal` |
| AI & Intelligence | __________________ | __________________ | `feature/ai-engine` |
| Backend/Database/Integration | __________________ | __________________ | `feature/backend-integration` |

### Every member must report at each checkpoint

Use this short update:

- **Completed:** Task IDs finished.
- **Working on:** Current task ID.
- **Blocked by:** Exact dependency or person needed.
- **Files changed:** List of owned files changed.
- **Ready for integration:** Yes/No.

### Final rule

The goal is not for four people to build four disconnected parts. The goal is one connected municipal workflow using two role-based portals, one backend, one database, one AI service and one shared map.

**Build the complaint-to-resolution flow first. Add the other features only after that flow works end to end.**
