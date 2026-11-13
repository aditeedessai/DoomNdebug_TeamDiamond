-- ==============================================================================
-- AI City Management Platform — Supabase PostgreSQL Database Schema
-- Task: M4-02 Supabase Database & Authentication
-- Author: Member 4 (Backend, Database & Integration Lead)
-- ==============================================================================

-- 1. EXTENSIONS
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ==============================================================================
-- 2. TABLE DEFINITIONS (In strict dependency order)
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- Table 1: departments
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.departments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------------------------
-- Table 2: profiles
-- Connects directly to Supabase auth.users using the same UUID
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'citizen' CHECK (role IN ('citizen', 'official', 'worker')),
    department_id UUID REFERENCES public.departments(id) ON DELETE SET NULL,
    is_safety_officer BOOLEAN NOT NULL DEFAULT false,
    phone TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------------------------
-- Table 3: complaints
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.complaints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    citizen_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    image_url TEXT,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    category TEXT NOT NULL,
    issue_type TEXT NOT NULL,
    department_id UUID REFERENCES public.departments(id) ON DELETE SET NULL,
    severity INTEGER NOT NULL DEFAULT 5 CHECK (severity BETWEEN 1 AND 10),
    priority TEXT NOT NULL DEFAULT 'Medium' CHECK (priority IN ('Low', 'Medium', 'High', 'Critical')),
    status TEXT NOT NULL DEFAULT 'Submitted' CHECK (status IN (
        'Submitted',
        'Under Review',
        'Assigned',
        'In Progress',
        'Resolved',
        'Rejected',
        'Needs More Information'
    )),
    master_incident_id UUID REFERENCES public.complaints(id) ON DELETE SET NULL,
    report_count INTEGER NOT NULL DEFAULT 1 CHECK (report_count >= 1),
    safety_related BOOLEAN NOT NULL DEFAULT false,
    safety_category TEXT,
    ai_summary TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------------------------
-- Table 4: complaint_updates
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.complaint_updates (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    complaint_id UUID NOT NULL REFERENCES public.complaints(id) ON DELETE CASCADE,
    actor_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    status TEXT NOT NULL CHECK (status IN (
        'Submitted',
        'Under Review',
        'Assigned',
        'In Progress',
        'Resolved',
        'Rejected',
        'Needs More Information'
    )),
    remarks TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------------------------
-- Table 5: projects
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.projects (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    department_id UUID NOT NULL REFERENCES public.departments(id) ON DELETE RESTRICT,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    start_date DATE NOT NULL,
    expected_end_date DATE NOT NULL,
    status TEXT NOT NULL DEFAULT 'Planned' CHECK (status IN ('Planned', 'Ongoing', 'Completed')),
    is_published BOOLEAN NOT NULL DEFAULT false,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_project_dates CHECK (expected_end_date >= start_date)
);

-- ------------------------------------------------------------------------------
-- Table 6: project_feedback
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.project_feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id UUID NOT NULL REFERENCES public.projects(id) ON DELETE CASCADE,
    citizen_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------------------------
-- Table 7: workers
-- Optional 1:1 relationship with profiles via UNIQUE profile_id
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.workers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    profile_id UUID UNIQUE REFERENCES public.profiles(id) ON DELETE SET NULL,
    name TEXT NOT NULL,
    department_id UUID NOT NULL REFERENCES public.departments(id) ON DELETE RESTRICT,
    availability TEXT NOT NULL DEFAULT 'Available' CHECK (availability IN ('Available', 'Busy', 'Unavailable')),
    phone TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------------------------
-- Table 8: traffic_hotspots
-- Created before assignments because assignments references traffic_hotspots
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.traffic_hotspots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    congestion_level TEXT NOT NULL DEFAULT 'Medium' CHECK (congestion_level IN ('Low', 'Medium', 'High')),
    source TEXT NOT NULL DEFAULT 'demo',
    observed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    description TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ------------------------------------------------------------------------------
-- Table 9: assignments
-- Ensures exactly one target is populated: complaint_id OR hotspot_id
-- ------------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS public.assignments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    complaint_id UUID REFERENCES public.complaints(id) ON DELETE CASCADE,
    hotspot_id UUID REFERENCES public.traffic_hotspots(id) ON DELETE CASCADE,
    worker_id UUID REFERENCES public.workers(id) ON DELETE SET NULL,
    officer_id UUID NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
    task_description TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Assigned' CHECK (status IN ('Assigned', 'In Progress', 'Completed')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT chk_assignment_target CHECK (
        (complaint_id IS NOT NULL AND hotspot_id IS NULL) OR
        (complaint_id IS NULL AND hotspot_id IS NOT NULL)
    )
);

-- ==============================================================================
-- 3. INDEXES FOR PERFORMANCE & FILTERING
-- ==============================================================================

-- Profiles indexes
CREATE INDEX IF NOT EXISTS idx_profiles_role ON public.profiles(role);
CREATE INDEX IF NOT EXISTS idx_profiles_department ON public.profiles(department_id);
CREATE INDEX IF NOT EXISTS idx_profiles_safety_officer ON public.profiles(is_safety_officer) WHERE is_safety_officer = true;

-- Complaints indexes
CREATE INDEX IF NOT EXISTS idx_complaints_citizen ON public.complaints(citizen_id);
CREATE INDEX IF NOT EXISTS idx_complaints_department ON public.complaints(department_id);
CREATE INDEX IF NOT EXISTS idx_complaints_status ON public.complaints(status);
CREATE INDEX IF NOT EXISTS idx_complaints_priority ON public.complaints(priority);
CREATE INDEX IF NOT EXISTS idx_complaints_created_at ON public.complaints(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_complaints_master_incident ON public.complaints(master_incident_id);
CREATE INDEX IF NOT EXISTS idx_complaints_safety ON public.complaints(safety_related) WHERE safety_related = true;
CREATE INDEX IF NOT EXISTS idx_complaints_coords ON public.complaints(latitude, longitude);

-- Complaint updates indexes
CREATE INDEX IF NOT EXISTS idx_complaint_updates_complaint ON public.complaint_updates(complaint_id);
CREATE INDEX IF NOT EXISTS idx_complaint_updates_actor ON public.complaint_updates(actor_id);
CREATE INDEX IF NOT EXISTS idx_complaint_updates_created_at ON public.complaint_updates(created_at DESC);

-- Projects indexes
CREATE INDEX IF NOT EXISTS idx_projects_department ON public.projects(department_id);
CREATE INDEX IF NOT EXISTS idx_projects_status ON public.projects(status);
CREATE INDEX IF NOT EXISTS idx_projects_published ON public.projects(is_published);

-- Project feedback indexes
CREATE INDEX IF NOT EXISTS idx_project_feedback_project ON public.project_feedback(project_id);
CREATE INDEX IF NOT EXISTS idx_project_feedback_citizen ON public.project_feedback(citizen_id);

-- Workers indexes
CREATE INDEX IF NOT EXISTS idx_workers_department ON public.workers(department_id);
CREATE INDEX IF NOT EXISTS idx_workers_availability ON public.workers(availability);
CREATE INDEX IF NOT EXISTS idx_workers_profile ON public.workers(profile_id);

-- Traffic hotspots indexes
CREATE INDEX IF NOT EXISTS idx_traffic_hotspots_observed ON public.traffic_hotspots(observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_traffic_hotspots_congestion ON public.traffic_hotspots(congestion_level);

-- Assignments indexes
CREATE INDEX IF NOT EXISTS idx_assignments_complaint ON public.assignments(complaint_id);
CREATE INDEX IF NOT EXISTS idx_assignments_hotspot ON public.assignments(hotspot_id);
CREATE INDEX IF NOT EXISTS idx_assignments_worker ON public.assignments(worker_id);
CREATE INDEX IF NOT EXISTS idx_assignments_officer ON public.assignments(officer_id);
CREATE INDEX IF NOT EXISTS idx_assignments_status ON public.assignments(status);

-- ==============================================================================
-- 4. TIMESTAMPTZ AUTO-UPDATE TRIGGERS
-- ==============================================================================

CREATE OR REPLACE FUNCTION public.update_timestamp_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_profiles_updated_at ON public.profiles;
CREATE TRIGGER trg_profiles_updated_at
BEFORE UPDATE ON public.profiles
FOR EACH ROW EXECUTE FUNCTION public.update_timestamp_column();

DROP TRIGGER IF EXISTS trg_complaints_updated_at ON public.complaints;
CREATE TRIGGER trg_complaints_updated_at
BEFORE UPDATE ON public.complaints
FOR EACH ROW EXECUTE FUNCTION public.update_timestamp_column();

DROP TRIGGER IF EXISTS trg_projects_updated_at ON public.projects;
CREATE TRIGGER trg_projects_updated_at
BEFORE UPDATE ON public.projects
FOR EACH ROW EXECUTE FUNCTION public.update_timestamp_column();

DROP TRIGGER IF EXISTS trg_workers_updated_at ON public.workers;
CREATE TRIGGER trg_workers_updated_at
BEFORE UPDATE ON public.workers
FOR EACH ROW EXECUTE FUNCTION public.update_timestamp_column();

DROP TRIGGER IF EXISTS trg_traffic_hotspots_updated_at ON public.traffic_hotspots;
CREATE TRIGGER trg_traffic_hotspots_updated_at
BEFORE UPDATE ON public.traffic_hotspots
FOR EACH ROW EXECUTE FUNCTION public.update_timestamp_column();

DROP TRIGGER IF EXISTS trg_assignments_updated_at ON public.assignments;
CREATE TRIGGER trg_assignments_updated_at
BEFORE UPDATE ON public.assignments
FOR EACH ROW EXECUTE FUNCTION public.update_timestamp_column();

-- ==============================================================================
-- 5. TASK 2: PROFILE CREATION & ROLE PROTECTION MECHANISMS
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- A. Trigger: Auto-create Profile upon Supabase Auth registration
-- Always assigns role = 'citizen' and is_safety_officer = false
-- ------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.profiles (
        id,
        full_name,
        role,
        department_id,
        is_safety_officer,
        phone,
        created_at,
        updated_at
    )
    VALUES (
        NEW.id,
        COALESCE(
            NEW.raw_user_meta_data->>'full_name',
            NEW.raw_user_meta_data->>'name',
            split_part(NEW.email, '@', 1),
            'Citizen User'
        ),
        'citizen', -- Always citizen by default
        NULL,      -- Citizens do not belong to municipal departments
        false,     -- Never a safety officer by default
        NEW.phone,
        now(),
        now()
    )
    ON CONFLICT (id) DO UPDATE SET
        full_name = EXCLUDED.full_name,
        phone = COALESCE(EXCLUDED.phone, public.profiles.phone),
        updated_at = now()
    WHERE public.profiles.role = 'citizen'; -- Only update citizen profile metadata
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Attach to Supabase auth.users
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
AFTER INSERT ON auth.users
FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- ------------------------------------------------------------------------------
-- B. Trigger: Role Protection Trigger
-- Blocks regular authenticated users from self-promoting to official or worker,
-- from altering their department, and from escalating is_safety_officer.
-- ------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.protect_profile_privileges()
RETURNS TRIGGER AS $$
BEGIN
    -- Check if execution is from a regular authenticated client (not service_role)
    IF (auth.role() = 'authenticated') THEN
        IF (NEW.role IS DISTINCT FROM OLD.role) THEN
            RAISE EXCEPTION 'Unauthorized: Users cannot modify their assigned role';
        END IF;

        IF (NEW.department_id IS DISTINCT FROM OLD.department_id) THEN
            RAISE EXCEPTION 'Unauthorized: Users cannot modify their department assignment';
        END IF;

        IF (NEW.is_safety_officer IS DISTINCT FROM OLD.is_safety_officer) THEN
            RAISE EXCEPTION 'Unauthorized: Users cannot modify safety officer status';
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS trg_protect_profile_privileges ON public.profiles;
CREATE TRIGGER trg_protect_profile_privileges
BEFORE UPDATE ON public.profiles
FOR EACH ROW EXECUTE FUNCTION public.protect_profile_privileges();

-- ==============================================================================
-- 6. TASK 3: ROW LEVEL SECURITY (RLS) POLICIES
-- ==============================================================================

-- Enable RLS on all 9 tables
ALTER TABLE public.departments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.complaints ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.complaint_updates ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.project_feedback ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.workers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.traffic_hotspots ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.assignments ENABLE ROW LEVEL SECURITY;

-- ------------------------------------------------------------------------------
-- RLS Helper Functions (SECURITY DEFINER for fast, secure policy checks)
-- ------------------------------------------------------------------------------
CREATE OR REPLACE FUNCTION public.is_official()
RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.profiles
        WHERE id = auth.uid() AND role = 'official'
    );
$$ LANGUAGE sql STABLE SECURITY DEFINER;

CREATE OR REPLACE FUNCTION public.is_safety_officer()
RETURNS BOOLEAN AS $$
    SELECT EXISTS (
        SELECT 1 FROM public.profiles
        WHERE id = auth.uid() AND role = 'official' AND is_safety_officer = true
    );
$$ LANGUAGE sql STABLE SECURITY DEFINER;

CREATE OR REPLACE FUNCTION public.get_user_department_id()
RETURNS UUID AS $$
    SELECT department_id FROM public.profiles
    WHERE id = auth.uid();
$$ LANGUAGE sql STABLE SECURITY DEFINER;

-- ------------------------------------------------------------------------------
-- Policies: departments
-- ------------------------------------------------------------------------------
DROP POLICY IF EXISTS "Departments viewable by everyone" ON public.departments;
CREATE POLICY "Departments viewable by everyone"
ON public.departments FOR SELECT
USING (true);

-- ------------------------------------------------------------------------------
-- Policies: profiles
-- ------------------------------------------------------------------------------
DROP POLICY IF EXISTS "Users can view own profile or officials can view all" ON public.profiles;
CREATE POLICY "Users can view own profile or officials can view all"
ON public.profiles FOR SELECT
USING (
    auth.uid() = id OR
    public.is_official() = true
);

DROP POLICY IF EXISTS "Users can update own profile" ON public.profiles;
CREATE POLICY "Users can update own profile"
ON public.profiles FOR UPDATE
USING (auth.uid() = id)
WITH CHECK (auth.uid() = id);

-- ------------------------------------------------------------------------------
-- Policies: complaints
-- ------------------------------------------------------------------------------
-- 1. Citizens view their own complaints
DROP POLICY IF EXISTS "Citizens view own complaints" ON public.complaints;
CREATE POLICY "Citizens view own complaints"
ON public.complaints FOR SELECT
USING (
    citizen_id = auth.uid()
);

-- 2. Officials view non-safety complaints matching their department (or general)
DROP POLICY IF EXISTS "Officials view non-safety complaints" ON public.complaints;
CREATE POLICY "Officials view non-safety complaints"
ON public.complaints FOR SELECT
USING (
    public.is_official() = true
    AND safety_related = false
    AND (department_id IS NULL OR department_id = public.get_user_department_id() OR public.get_user_department_id() IS NULL)
);

-- 3. Designated safety officers view safety-related complaints
DROP POLICY IF EXISTS "Designated safety officers view safety complaints" ON public.complaints;
CREATE POLICY "Designated safety officers view safety complaints"
ON public.complaints FOR SELECT
USING (
    public.is_safety_officer() = true
    AND safety_related = true
);

-- 4. Citizens insert complaints for themselves
DROP POLICY IF EXISTS "Citizens insert own complaints" ON public.complaints;
CREATE POLICY "Citizens insert own complaints"
ON public.complaints FOR INSERT
WITH CHECK (
    citizen_id = auth.uid()
);

-- 5. Citizens update their own draft/submitted complaints
DROP POLICY IF EXISTS "Citizens update submitted complaints" ON public.complaints;
CREATE POLICY "Citizens update submitted complaints"
ON public.complaints FOR UPDATE
USING (
    citizen_id = auth.uid()
    AND status IN ('Submitted', 'Needs More Information')
)
WITH CHECK (
    citizen_id = auth.uid()
    AND status IN ('Submitted', 'Needs More Information')
);

-- 6. Officials update permitted complaints
DROP POLICY IF EXISTS "Officials update permitted complaints" ON public.complaints;
CREATE POLICY "Officials update permitted complaints"
ON public.complaints FOR UPDATE
USING (
    public.is_official() = true
    AND (
        (safety_related = false AND (department_id IS NULL OR department_id = public.get_user_department_id() OR public.get_user_department_id() IS NULL))
        OR (safety_related = true AND public.is_safety_officer() = true)
    )
);

-- ------------------------------------------------------------------------------
-- Policies: complaint_updates
-- ------------------------------------------------------------------------------
DROP POLICY IF EXISTS "View complaint updates" ON public.complaint_updates;
CREATE POLICY "View complaint updates"
ON public.complaint_updates FOR SELECT
USING (
    EXISTS (
        SELECT 1 FROM public.complaints c
        WHERE c.id = public.complaint_updates.complaint_id
        AND (
            c.citizen_id = auth.uid()
            OR (public.is_official() = true AND (
                (c.safety_related = false AND (c.department_id IS NULL OR c.department_id = public.get_user_department_id() OR public.get_user_department_id() IS NULL))
                OR (c.safety_related = true AND public.is_safety_officer() = true)
            ))
        )
    )
);

DROP POLICY IF EXISTS "Officials insert complaint updates" ON public.complaint_updates;
CREATE POLICY "Officials insert complaint updates"
ON public.complaint_updates FOR INSERT
WITH CHECK (
    public.is_official() = true
    AND actor_id = auth.uid()
);

-- ------------------------------------------------------------------------------
-- Policies: projects
-- ------------------------------------------------------------------------------
DROP POLICY IF EXISTS "Public views published projects and officials view all" ON public.projects;
CREATE POLICY "Public views published projects and officials view all"
ON public.projects FOR SELECT
USING (
    is_published = true OR public.is_official() = true
);

DROP POLICY IF EXISTS "Officials insert projects" ON public.projects;
CREATE POLICY "Officials insert projects"
ON public.projects FOR INSERT
WITH CHECK (public.is_official() = true);

DROP POLICY IF EXISTS "Officials update projects" ON public.projects;
CREATE POLICY "Officials update projects"
ON public.projects FOR UPDATE
USING (public.is_official() = true);

-- ------------------------------------------------------------------------------
-- Policies: project_feedback
-- ------------------------------------------------------------------------------
DROP POLICY IF EXISTS "Citizens view own feedback" ON public.project_feedback;
CREATE POLICY "Citizens view own feedback"
ON public.project_feedback FOR SELECT
USING (citizen_id = auth.uid());

DROP POLICY IF EXISTS "Officials view feedback for department projects" ON public.project_feedback;
CREATE POLICY "Officials view feedback for department projects"
ON public.project_feedback FOR SELECT
USING (
    public.is_official() = true
    AND EXISTS (
        SELECT 1 FROM public.projects p
        WHERE p.id = public.project_feedback.project_id
        AND (p.department_id = public.get_user_department_id() OR public.get_user_department_id() IS NULL)
    )
);

DROP POLICY IF EXISTS "Citizens submit project feedback" ON public.project_feedback;
CREATE POLICY "Citizens submit project feedback"
ON public.project_feedback FOR INSERT
WITH CHECK (citizen_id = auth.uid());

-- ------------------------------------------------------------------------------
-- Policies: workers
-- ------------------------------------------------------------------------------
DROP POLICY IF EXISTS "Officials and assigned workers view workers" ON public.workers;
CREATE POLICY "Officials and assigned workers view workers"
ON public.workers FOR SELECT
USING (
    public.is_official() = true OR profile_id = auth.uid()
);

DROP POLICY IF EXISTS "Officials manage workers" ON public.workers;
CREATE POLICY "Officials manage workers"
ON public.workers FOR ALL
USING (public.is_official() = true);

-- ------------------------------------------------------------------------------
-- Policies: traffic_hotspots
-- ------------------------------------------------------------------------------
DROP POLICY IF EXISTS "Traffic hotspots viewable by authenticated users" ON public.traffic_hotspots;
CREATE POLICY "Traffic hotspots viewable by authenticated users"
ON public.traffic_hotspots FOR SELECT
USING (auth.role() = 'authenticated');

DROP POLICY IF EXISTS "Officials manage traffic hotspots" ON public.traffic_hotspots;
CREATE POLICY "Officials manage traffic hotspots"
ON public.traffic_hotspots FOR ALL
USING (public.is_official() = true);

-- ------------------------------------------------------------------------------
-- Policies: assignments
-- ------------------------------------------------------------------------------
DROP POLICY IF EXISTS "Officials and assigned workers view assignments" ON public.assignments;
CREATE POLICY "Officials and assigned workers view assignments"
ON public.assignments FOR SELECT
USING (
    public.is_official() = true
    OR officer_id = auth.uid()
    OR worker_id IN (SELECT id FROM public.workers WHERE profile_id = auth.uid())
);

DROP POLICY IF EXISTS "Officials manage assignments" ON public.assignments;
CREATE POLICY "Officials manage assignments"
ON public.assignments FOR ALL
USING (public.is_official() = true)
WITH CHECK (public.is_official() = true AND officer_id = auth.uid());

