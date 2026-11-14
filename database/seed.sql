-- ==============================================================================
-- AI City Management Platform — Supabase Seed Data
-- Tasks: M4-02 Database Foundation & M4-10 Seed Data & Demo Scenarios
-- Authors: Member 4 (Backend, Database & Integration Lead)
--
-- This script provisions baseline municipal data and realistic demo records
-- supporting end-to-end demonstrations across both Citizen and Official Portals.
--
-- Supported PRD Scenarios:
--   Scenario A: Road Infrastructure and Potholes (with duplicate detection pair)
--   Scenario B: Citizen Project Feedback on Ongoing Municipal Infrastructure
--   Scenario C: Women's Infrastructure Safety (Dark corridor k >= 3 cluster)
--   Scenario D: Traffic Hotspot Response & Municipal Field Worker Dispatch
--
-- IDEMPOTENCY:
--   All inserts use deterministic UUIDs and ON CONFLICT (id) DO UPDATE clauses.
--   Safe to execute repeatedly without duplicating data.
--
-- AUTH DEPENDENCIES:
--   Records in public.profiles reference auth.users(id). Profile-dependent demo
--   records (complaints, feedback, assignments) are guarded in a PL/pgSQL block
--   that safely resolves existing profiles, or emits informative NOTICE messages
--   and skips dependent tables if demo users have not yet been provisioned.
-- ==============================================================================

-- ------------------------------------------------------------------------------
-- 1. SEED DEPARTMENTS
-- Deterministic UUIDs used for repeatable local and staging seed operations.
-- ------------------------------------------------------------------------------
INSERT INTO public.departments (id, name, description)
VALUES
    ('11111111-1111-1111-1111-111111111111', 'Public Works Department', 'Road maintenance, bridges, sidewalks, and civil structures.'),
    ('22222222-2222-2222-2222-222222222222', 'Sanitation Department', 'Waste management, public bin clearance, and street cleanliness.'),
    ('33333333-3333-3333-3333-333333333333', 'Electrical Department', 'Street lighting, traffic signal power, and electrical infrastructure.'),
    ('44444444-4444-4444-4444-444444444444', 'Water & Sewerage Department', 'Drinking water supply pipelines, sewer line drainage, and manholes.'),
    ('55555555-5555-5555-5555-555555555555', 'Traffic & Transport Department', 'Traffic flow management, public bus stops, and road signage.'),
    ('66666666-6666-6666-6666-666666666666', 'Parks & Public Assets Department', 'Public gardens, trees, municipal buildings, and community centers.')
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    description = EXCLUDED.description;

-- ------------------------------------------------------------------------------
-- 2. SEED WORKERS (Field Teams)
-- ------------------------------------------------------------------------------
INSERT INTO public.workers (id, name, department_id, availability, phone)
VALUES
    ('aaaaaaaa-1111-0000-0000-000000000001', 'PWD Rapid Repair Crew Alpha', '11111111-1111-1111-1111-111111111111', 'Available', '+91 98765 00001'),
    ('aaaaaaaa-1111-0000-0000-000000000002', 'PWD Asphalt Paving Team Beta', '11111111-1111-1111-1111-111111111111', 'Busy', '+91 98765 00002'),
    ('bbbbbbbb-2222-0000-0000-000000000001', 'Sanitation Ward Clean Squad 1', '22222222-2222-2222-2222-222222222222', 'Available', '+91 98765 00003'),
    ('bbbbbbbb-2222-0000-0000-000000000002', 'Sanitation Ward Clean Squad 2', '22222222-2222-2222-2222-222222222222', 'Available', '+91 98765 00004'),
    ('cccccccc-3333-0000-0000-000000000001', 'Electrical Streetlight Unit A', '33333333-3333-3333-3333-333333333333', 'Available', '+91 98765 00005'),
    ('dddddddd-4444-0000-0000-000000000001', 'Water Pipeline Emergency Team', '44444444-4444-4444-4444-444444444444', 'Busy', '+91 98765 00006'),
    ('eeeeeeee-5555-0000-0000-000000000001', 'Traffic Signal Maintenance Crew', '55555555-5555-5555-5555-555555555555', 'Available', '+91 98765 00007'),
    ('ffffffff-6666-0000-0000-000000000001', 'Parks & Tree Pruning Squad', '66666666-6666-6666-6666-666666666666', 'Available', '+91 98765 00008')
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    department_id = EXCLUDED.department_id,
    availability = EXCLUDED.availability;

-- ------------------------------------------------------------------------------
-- 3. SEED PUBLISHED PROJECTS
-- ------------------------------------------------------------------------------
INSERT INTO public.projects (id, title, description, department_id, latitude, longitude, start_date, expected_end_date, status, is_published)
VALUES
    (
        '99999999-0001-0000-0000-000000000001',
        'Smart Bus Shelter & LED Corridor Upgrades',
        'Installation of solar-powered lighting, safety SOS alarms, and weather shelters along Central Avenue.',
        '55555555-5555-5555-5555-555555555555',
        15.3995,
        73.8122,
        '2026-01-15',
        '2026-06-30',
        'Ongoing',
        true
    ),
    (
        '99999999-0002-0000-0000-000000000002',
        'North Ward Underground Drainage Rehabilitation',
        'Replacing degraded stormwater pipes to alleviate seasonal monsoon waterlogging and road erosion.',
        '44444444-4444-4444-4444-444444444444',
        15.4050,
        73.8180,
        '2026-02-01',
        '2026-08-30',
        'Ongoing',
        true
    ),
    (
        '99999999-0003-0000-0000-000000000003',
        'High-Mast Solar Lighting at Market Junction',
        'Enhancing illumination in high-pedestrian commercial zones and transit points for pedestrian safety.',
        '33333333-3333-3333-3333-333333333333',
        15.3920,
        73.8050,
        '2026-03-01',
        '2026-05-15',
        'Completed',
        true
    ),
    (
        '99999999-0004-0000-0000-000000000004',
        'City Ring Road Flyover Expansion',
        'Major infrastructure expansion connecting East Bypass to Port Highway with dedicated bus transit lanes.',
        '11111111-1111-1111-1111-111111111111',
        15.4120,
        73.8250,
        '2026-04-01',
        '2027-04-01',
        'Planned',
        true
    )
ON CONFLICT (id) DO UPDATE SET
    title = EXCLUDED.title,
    description = EXCLUDED.description,
    status = EXCLUDED.status,
    is_published = EXCLUDED.is_published;

-- ------------------------------------------------------------------------------
-- 4. SEED TRAFFIC HOTSPOTS
-- ------------------------------------------------------------------------------
INSERT INTO public.traffic_hotspots (id, latitude, longitude, congestion_level, source, observed_at, description)
VALUES
    (
        '88888888-0001-0000-0000-000000000001',
        15.4010,
        73.8150,
        'High',
        'demo',
        now() - INTERVAL '15 minutes',
        'Market Cross Junction: Heavy congestion due to temporary utility trenching and high evening peak volume.'
    ),
    (
        '88888888-0002-0000-0000-000000000002',
        15.3940,
        73.8090,
        'Medium',
        'demo',
        now() - INTERVAL '30 minutes',
        'Railway Overbridge Approach: Moderate vehicle slowdown caused by stalled transit bus on north lane.'
    ),
    (
        '88888888-0003-0000-0000-000000000003',
        15.4150,
        73.8300,
        'Low',
        'demo',
        now() - INTERVAL '45 minutes',
        'Bypass Roundabout: Normal vehicle flow with minor signal queue during school dismissal hours.'
    )
ON CONFLICT (id) DO UPDATE SET
    congestion_level = EXCLUDED.congestion_level,
    description = EXCLUDED.description;

-- ==============================================================================
-- 5. ADMINISTRATIVE INSTRUCTIONS FOR DEMO ACCOUNTS
-- ==============================================================================
-- To provision official and worker demo accounts in Supabase:
--
-- 1. Create the user accounts in Supabase Auth Dashboard (or via Admin API).
--    Administrators must set secure temporary passwords through the Supabase Auth
--    Dashboard or approved administrative workflow:
--    - Citizen User:   citizen@city.gov
--    - Official User:  official@city.gov
--    - Safety Officer: safety.official@city.gov
--    - Worker User:    worker@city.gov
--
-- 2. Execute SQL with the resulting Auth UUIDs (replace '<AUTH_USER_UUID>'):
--
--    -- Promote to PWD Official:
--    UPDATE public.profiles
--    SET role = 'official',
--        department_id = '11111111-1111-1111-1111-111111111111',
--        is_safety_officer = false
--    WHERE id = '<OFFICIAL_AUTH_UUID>';
--
--    -- Promote to Designated Safety Official:
--    UPDATE public.profiles
--    SET role = 'official',
--        department_id = '33333333-3333-3333-3333-333333333333',
--        is_safety_officer = true
--    WHERE id = '<SAFETY_OFFICIAL_AUTH_UUID>';
--
--    -- Promote to Worker & Link Worker Record:
--    UPDATE public.profiles
--    SET role = 'worker',
--        department_id = '11111111-1111-1111-1111-111111111111'
--    WHERE id = '<WORKER_AUTH_UUID>';
--
--    UPDATE public.workers
--    SET profile_id = '<WORKER_AUTH_UUID>'
--    WHERE id = 'aaaaaaaa-1111-0000-0000-000000000001';
--
-- 3. Re-run this script (seed.sql) to automatically populate all demo complaints,
--    updates, feedback, and worker assignments below.
-- ==============================================================================

-- ==============================================================================
-- 6. PROFILE-DEPENDENT DEMO DATA (SCENARIOS A, B, C, D)
-- ==============================================================================
DO $$
DECLARE
    v_citizen_id UUID;
    v_official_id UUID;
    v_safety_official_id UUID;
BEGIN
    -- --------------------------------------------------------------------------
    -- A. Resolve Profiles
    -- Specifically identify the designated demo accounts joined through auth.users.
    -- Do NOT fall back to arbitrary existing profiles to prevent attaching demo
    -- data to real user accounts.
    -- --------------------------------------------------------------------------
    -- 1. Resolve Demo Citizen Profile (citizen@city.gov)
    SELECT p.id INTO v_citizen_id
    FROM public.profiles p
    JOIN auth.users u ON p.id = u.id
    WHERE lower(u.email) = 'citizen@city.gov'
      AND p.role = 'citizen'
    LIMIT 1;

    -- 2. Resolve Demo General Official Profile (official@city.gov)
    SELECT p.id INTO v_official_id
    FROM public.profiles p
    JOIN auth.users u ON p.id = u.id
    WHERE lower(u.email) = 'official@city.gov'
      AND p.role = 'official'
    LIMIT 1;

    -- 3. Resolve Designated Safety Officer Profile (safety.official@city.gov)
    -- Strictly requires role = 'official' AND is_safety_officer = true.
    -- No fallback to ordinary officials.
    SELECT p.id INTO v_safety_official_id
    FROM public.profiles p
    JOIN auth.users u ON p.id = u.id
    WHERE lower(u.email) = 'safety.official@city.gov'
      AND p.role = 'official'
      AND p.is_safety_officer = true
    LIMIT 1;

    -- --------------------------------------------------------------------------
    -- B. Verify Citizen Profile Availability
    -- --------------------------------------------------------------------------
    IF v_citizen_id IS NULL THEN
        RAISE NOTICE '====================================================================';
        RAISE NOTICE 'SEED NOTICE: Demo citizen profile (citizen@city.gov) not found in';
        RAISE NOTICE 'public.profiles joined with auth.users. Skipping demo complaints,';
        RAISE NOTICE 'timeline updates, and project feedback seeding.';
        RAISE NOTICE 'Please create citizen@city.gov in Supabase Auth, then re-run seed.sql.';
        RAISE NOTICE '====================================================================';
    ELSE
        RAISE NOTICE 'Seeding demo complaints and feedback using citizen profile ID: %', v_citizen_id;

        -- ----------------------------------------------------------------------
        -- B1. SCENARIO A: ROAD INFRASTRUCTURE COMPLAINTS & DUPLICATE PAIR
        -- ----------------------------------------------------------------------
        -- Master Complaint 1: Pothole on Bus Stand Road
        INSERT INTO public.complaints (
            id, citizen_id, title, description, image_url,
            latitude, longitude, category, issue_type,
            department_id, severity, priority, status,
            report_count, safety_related, safety_category, ai_summary
        ) VALUES (
            '10101010-0001-0000-0000-000000000001',
            v_citizen_id,
            'Large dangerous pothole near Central Bus Stand',
            'Deep pothole roughly 2 feet wide on the north carriageway near Central Bus Stand. Poses severe skid hazard for two-wheelers during peak traffic.',
            NULL,
            15.4005, 73.8130,
            'Pothole', 'Road Damage',
            '11111111-1111-1111-1111-111111111111', -- PWD
            8, 'High', 'In Progress',
            2, false, NULL,
            'Severe road pothole located near Central Bus Stand creating two-wheeler skid hazards. Routed to Public Works Department.'
        ) ON CONFLICT (id) DO UPDATE SET
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            status = EXCLUDED.status,
            report_count = EXCLUDED.report_count;

        -- Duplicate Child Complaint 1B: Nearby complaint to demonstrate duplicate linking
        INSERT INTO public.complaints (
            id, citizen_id, title, description, image_url,
            latitude, longitude, category, issue_type,
            department_id, severity, priority, status,
            master_incident_id, report_count, safety_related, safety_category, ai_summary
        ) VALUES (
            '10101010-0001-0000-0000-000000000002',
            v_citizen_id,
            'Broken asphalt crater next to bus terminus exit',
            'Road surface broken and sunk in outside central bus stand exit gate. Two-wheelers swerving dangerously into oncoming traffic.',
            NULL,
            15.4007, 73.8132,
            'Pothole', 'Road Damage',
            '11111111-1111-1111-1111-111111111111', -- PWD
            7, 'Medium', 'Submitted',
            '10101010-0001-0000-0000-000000000001', -- Linked duplicate child
            1, false, NULL,
            'Advisory duplicate candidate linked to master incident 10101010-0001-0000-0000-000000000001.'
        ) ON CONFLICT (id) DO UPDATE SET
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            master_incident_id = EXCLUDED.master_incident_id;

        -- Complaint 2: Overflowing Sanitation Waste
        INSERT INTO public.complaints (
            id, citizen_id, title, description, image_url,
            latitude, longitude, category, issue_type,
            department_id, severity, priority, status,
            report_count, safety_related, safety_category, ai_summary
        ) VALUES (
            '10101010-0002-0000-0000-000000000001',
            v_citizen_id,
            'Overflowing garbage bin blocking market lane',
            'Municipal waste container at Market Lane has been overflowing for 3 days. Trash spilling across sidewalk into road lane causing foul odor and blocking shoppers.',
            NULL,
            15.3980, 73.8105,
            'Garbage', 'Waste Management',
            '22222222-2222-2222-2222-222222222222', -- Sanitation
            6, 'Medium', 'Assigned',
            1, false, NULL,
            'Municipal bin overflow blocking pedestrian and lane access at Market Lane. Assigned to Sanitation Department.'
        ) ON CONFLICT (id) DO UPDATE SET
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            status = EXCLUDED.status;

        -- Complaint 3: Water Pipeline Leak
        INSERT INTO public.complaints (
            id, citizen_id, title, description, image_url,
            latitude, longitude, category, issue_type,
            department_id, severity, priority, status,
            report_count, safety_related, safety_category, ai_summary
        ) VALUES (
            '10101010-0003-0000-0000-000000000001',
            v_citizen_id,
            'Underground drinking water main leak flooding 2nd Cross',
            'High-pressure clean water gushing from cracked underground pipe joint. Road partially eroded and water pressure dropping in neighborhood houses.',
            NULL,
            15.4070, 73.8200,
            'Water Leak', 'Pipeline Burst',
            '44444444-4444-4444-4444-444444444444', -- Water & Sewerage
            8, 'Critical', 'Under Review',
            1, false, NULL,
            'High-pressure drinking water main leak eroding 2nd Cross road surface. Urgent pipeline repair needed.'
        ) ON CONFLICT (id) DO UPDATE SET
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            status = EXCLUDED.status;

        -- Complaint 4: Resolved Public Parks Issue
        INSERT INTO public.complaints (
            id, citizen_id, title, description, image_url,
            latitude, longitude, category, issue_type,
            department_id, severity, priority, status,
            report_count, safety_related, safety_category, ai_summary
        ) VALUES (
            '10101010-0005-0000-0000-000000000001',
            v_citizen_id,
            'Fallen gulmohar tree branch blocking park avenue walkway',
            'Large tree branch fell during heavy monsoon gusts across the community park entrance path.',
            NULL,
            15.4030, 73.8160,
            'Parks', 'Obstruction Removal',
            '66666666-6666-6666-6666-666666666666', -- Parks & Public Assets
            4, 'Low', 'Resolved',
            1, false, NULL,
            'Fallen tree branch cleared from park avenue walkway. Public access restored.'
        ) ON CONFLICT (id) DO UPDATE SET
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            status = EXCLUDED.status;

        -- ----------------------------------------------------------------------
        -- B2. SCENARIO C: WOMEN'S INFRASTRUCTURE SAFETY (CLUSTERING k >= 3)
        -- Reports situated in close proximity (~150m apart near Metro South)
        -- Coordinates round to identical (15.39, 73.81) for k >= 3 aggregation
        -- ----------------------------------------------------------------------
        -- Safety Report 1: Dark subway access
        INSERT INTO public.complaints (
            id, citizen_id, title, description, image_url,
            latitude, longitude, category, issue_type,
            department_id, severity, priority, status,
            report_count, safety_related, safety_category, ai_summary
        ) VALUES (
            '10101010-0004-0000-0000-000000000001',
            v_citizen_id,
            'Non-functional streetlights along pedestrian subway path',
            'Four consecutive sodium streetlights out of order along the dark pedestrian access walkway to Metro South gate. Corridor completely unlit after 7 PM.',
            NULL,
            15.3918, 73.8052,
            'Lighting', 'Dark Corridor / Streetlight Failure',
            '33333333-3333-3333-3333-333333333333', -- Electrical
            8, 'High', 'Submitted',
            1, true, 'Lighting',
            'Restricted safety report: Dark pedestrian corridor with consecutive streetlight outages near transit exit. Elevated harassment risk.'
        ) ON CONFLICT (id) DO UPDATE SET
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            status = EXCLUDED.status;

        -- Safety Report 2: Dark bus bay overgrowth
        INSERT INTO public.complaints (
            id, citizen_id, title, description, image_url,
            latitude, longitude, category, issue_type,
            department_id, severity, priority, status,
            report_count, safety_related, safety_category, ai_summary
        ) VALUES (
            '10101010-0004-0000-0000-000000000002',
            v_citizen_id,
            'Dark overgrown footpath and broken lampposts at Metro South bus bay',
            'Overhanging foliage obscuring broken streetlamp at Metro South feeder bus bay. Zero visibility for women commuters waiting for evening transit.',
            NULL,
            15.3922, 73.8055,
            'Lighting', 'Dark Corridor / Overgrowth',
            '33333333-3333-3333-3333-333333333333', -- Electrical
            9, 'Critical', 'Under Review',
            1, true, 'Lighting',
            'Restricted safety report: Broken lamp and unlit bus bay at Metro South. High severity transit safety concern.'
        ) ON CONFLICT (id) DO UPDATE SET
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            status = EXCLUDED.status;

        -- Safety Report 3: Unlit walkway near women's hostel
        INSERT INTO public.complaints (
            id, citizen_id, title, description, image_url,
            latitude, longitude, category, issue_type,
            department_id, severity, priority, status,
            report_count, safety_related, safety_category, ai_summary
        ) VALUES (
            '10101010-0004-0000-0000-000000000003',
            v_citizen_id,
            'Unlit park peripheral walkway near women hostel',
            'Streetlamps completely dead on the 200m walkway stretch adjacent to Municipal Park and working women hostel. No CCTV or functional lights.',
            NULL,
            15.3925, 73.8058,
            'Lighting', 'Dark Corridor / Streetlight Outage',
            '33333333-3333-3333-3333-333333333333', -- Electrical
            8, 'High', 'Assigned',
            1, true, 'Lighting',
            'Restricted safety report: Unlit peripheral walkway near women hostel. High severity lighting hazard.'
        ) ON CONFLICT (id) DO UPDATE SET
            title = EXCLUDED.title,
            description = EXCLUDED.description,
            status = EXCLUDED.status;

        -- ----------------------------------------------------------------------
        -- B3. COMPLAINT TIMELINE HISTORY (public.complaint_updates)
        -- ----------------------------------------------------------------------
        -- 1. Base Citizen Submission Timeline Entries (Updates 1, 4, 6, 7, 8, 9)
        INSERT INTO public.complaint_updates (id, complaint_id, actor_id, status, remarks, created_at)
        VALUES
            (
                '20202020-0001-0000-0000-000000000001',
                '10101010-0001-0000-0000-000000000001',
                v_citizen_id,
                'Submitted',
                'Civic complaint registered via citizen portal with description and coordinates.',
                now() - INTERVAL '3 hours'
            ),
            (
                '20202020-0002-0000-0000-000000000001',
                '10101010-0002-0000-0000-000000000001',
                v_citizen_id,
                'Submitted',
                'Citizen reported severe commercial waste bin overflow at Market Lane.',
                now() - INTERVAL '4 hours'
            ),
            (
                '20202020-0003-0000-0000-000000000001',
                '10101010-0003-0000-0000-000000000001',
                v_citizen_id,
                'Submitted',
                'Water pipeline burst reported flooding 2nd Cross road.',
                now() - INTERVAL '50 minutes'
            ),
            (
                '20202020-0004-0000-0000-000000000001',
                '10101010-0004-0000-0000-000000000001',
                v_citizen_id,
                'Submitted',
                'Safety infrastructure report submitted: dark pedestrian subway corridor.',
                now() - INTERVAL '6 hours'
            ),
            (
                '20202020-0004-0000-0000-000000000002',
                '10101010-0004-0000-0000-000000000002',
                v_citizen_id,
                'Submitted',
                'Safety infrastructure report submitted: overgrown dark bus bay.',
                now() - INTERVAL '4 hours'
            ),
            (
                '20202020-0004-0000-0000-000000000003',
                '10101010-0004-0000-0000-000000000003',
                v_citizen_id,
                'Submitted',
                'Safety infrastructure report submitted: unlit walkway near women hostel.',
                now() - INTERVAL '2 hours'
            )
        ON CONFLICT (id) DO UPDATE SET
            status = EXCLUDED.status,
            remarks = EXCLUDED.remarks;

        -- 2. Official Timeline Updates (Updates 2, 3, 5 - Requires v_official_id)
        IF v_official_id IS NOT NULL THEN
            INSERT INTO public.complaint_updates (id, complaint_id, actor_id, status, remarks, created_at)
            VALUES
                (
                    '20202020-0001-0000-0000-000000000002',
                    '10101010-0001-0000-0000-000000000001',
                    v_official_id,
                    'Assigned',
                    'Reviewed by municipal desk and dispatched to PWD Rapid Repair Crew Alpha.',
                    now() - INTERVAL '2 hours'
                ),
                (
                    '20202020-0001-0000-0000-000000000003',
                    '10101010-0001-0000-0000-000000000001',
                    v_official_id,
                    'In Progress',
                    'Field crew arrived on-site at Central Bus Stand. Cold-mix asphalt repair initiated.',
                    now() - INTERVAL '45 minutes'
                ),
                (
                    '20202020-0002-0000-0000-000000000002',
                    '10101010-0002-0000-0000-000000000001',
                    v_official_id,
                    'Assigned',
                    'Routed to Sanitation Ward Clean Squad 1 for scheduled clearing.',
                    now() - INTERVAL '1 hour'
                )
            ON CONFLICT (id) DO UPDATE SET
                status = EXCLUDED.status,
                remarks = EXCLUDED.remarks;
        ELSE
            RAISE NOTICE 'SEED NOTICE: Demo official profile (official@city.gov) not found.';
            RAISE NOTICE 'Skipping demo official complaint timeline updates.';
        END IF;

        -- 3. Safety Officer Timeline Update (Update 10 - Requires v_safety_official_id)
        IF v_safety_official_id IS NOT NULL THEN
            INSERT INTO public.complaint_updates (id, complaint_id, actor_id, status, remarks, created_at)
            VALUES
                (
                    '20202020-0004-0000-0000-000000000004',
                    '10101010-0004-0000-0000-000000000003',
                    v_safety_official_id,
                    'Assigned',
                    'Designated safety officer prioritized high-mast and fixture repair with Electrical Unit A.',
                    now() - INTERVAL '30 minutes'
                )
            ON CONFLICT (id) DO UPDATE SET
                status = EXCLUDED.status,
                remarks = EXCLUDED.remarks;
        ELSE
            RAISE NOTICE 'SEED NOTICE: Demo safety official profile (safety.official@city.gov) not found.';
            RAISE NOTICE 'Skipping demo safety officer complaint timeline update.';
        END IF;

        -- ----------------------------------------------------------------------
        -- B4. SCENARIO B: CITIZEN PROJECT FEEDBACK (public.project_feedback)
        -- ----------------------------------------------------------------------
        INSERT INTO public.project_feedback (id, project_id, citizen_id, category, message, created_at)
        VALUES
            (
                '30303030-0001-0000-0000-000000000001',
                '99999999-0004-0000-0000-000000000004', -- City Ring Road Flyover
                v_citizen_id,
                'road closures/diversions',
                'Flyover construction barricades completely block the pedestrian zebra crossing at Port Highway junction. Pedestrians forced into fast-moving vehicle lanes.',
                now() - INTERVAL '2 days'
            ),
            (
                '30303030-0002-0000-0000-000000000001',
                '99999999-0001-0000-0000-000000000001', -- Smart Bus Shelter Upgrades
                v_citizen_id,
                'accessibility',
                'The newly elevated curb at Central Avenue shelter lacks a wheelchair ramp. Elderly citizens and disabled passengers cannot board low-floor buses safely.',
                now() - INTERVAL '1 day'
            ),
            (
                '30303030-0003-0000-0000-000000000001',
                '99999999-0002-0000-0000-000000000002', -- Drainage Rehabilitation
                v_citizen_id,
                'construction inconvenience',
                'Uncovered trenching left open without safety reflectors overnight outside Ward residential lane. Dust levels very high.',
                now() - INTERVAL '12 hours'
            )
        ON CONFLICT (id) DO UPDATE SET
            category = EXCLUDED.category,
            message = EXCLUDED.message;

    END IF;

    -- --------------------------------------------------------------------------
    -- C. SCENARIO D: ASSIGNMENTS (public.assignments)
    -- --------------------------------------------------------------------------

    -- C1. Ordinary Assignments (Complaint & Hotspot)
    -- Requires valid general official profile (official@city.gov)
    IF v_official_id IS NULL THEN
        RAISE NOTICE '====================================================================';
        RAISE NOTICE 'SEED NOTICE: Demo official profile (official@city.gov) not found in';
        RAISE NOTICE 'public.profiles joined with auth.users. Skipping demo ordinary';
        RAISE NOTICE 'complaint and hotspot assignments seeding.';
        RAISE NOTICE 'Please create official@city.gov in Supabase Auth, promote to official,';
        RAISE NOTICE 'then re-run seed.sql.';
        RAISE NOTICE '====================================================================';
    ELSE
        RAISE NOTICE 'Seeding demo ordinary assignments using official profile ID: %', v_official_id;

        -- Assignment 1: Complaint Assignment (Pothole -> PWD Rapid Repair Crew Alpha)
        IF v_citizen_id IS NOT NULL THEN
            INSERT INTO public.assignments (
                id, complaint_id, hotspot_id, worker_id, officer_id, task_description, status, created_at, updated_at
            ) VALUES (
                '40404040-0001-0000-0000-000000000001',
                '10101010-0001-0000-0000-000000000001', -- Central Bus Stand Pothole
                NULL,
                'aaaaaaaa-1111-0000-0000-000000000001', -- PWD Rapid Repair Crew Alpha
                v_official_id,
                'Inspect Central Bus Stand pothole and lay cold-mix asphalt patch to eliminate skid hazards.',
                'In Progress',
                now() - INTERVAL '2 hours',
                now() - INTERVAL '45 minutes'
            ) ON CONFLICT (id) DO UPDATE SET
                task_description = EXCLUDED.task_description,
                status = EXCLUDED.status;
        END IF;

        -- Assignment 2: Traffic Hotspot Assignment (Market Cross -> Traffic Signal Crew)
        INSERT INTO public.assignments (
            id, complaint_id, hotspot_id, worker_id, officer_id, task_description, status, created_at, updated_at
        ) VALUES (
            '40404040-0002-0000-0000-000000000001',
            NULL,
            '88888888-0001-0000-0000-000000000001', -- Market Cross Junction Hotspot
            'eeeeeeee-5555-0000-0000-000000000001', -- Traffic Signal Maintenance Crew
            v_official_id,
            'Override traffic signal cycle timing and deploy manual traffic control during evening peak.',
            'Assigned',
            now() - INTERVAL '15 minutes',
            now() - INTERVAL '15 minutes'
        ) ON CONFLICT (id) DO UPDATE SET
            task_description = EXCLUDED.task_description,
            status = EXCLUDED.status;

    END IF;

    -- C2. Safety Assignment (Dark Corridor Walkway -> Electrical Unit A)
    -- Strictly requires designated safety officer profile (safety.official@city.gov).
    -- Does NOT fall back to general official!
    IF v_safety_official_id IS NULL THEN
        RAISE NOTICE '====================================================================';
        RAISE NOTICE 'SEED NOTICE: Demo safety official profile (safety.official@city.gov)';
        RAISE NOTICE 'with role="official" and is_safety_officer=true not found in';
        RAISE NOTICE 'public.profiles joined with auth.users.';
        RAISE NOTICE 'Skipping demo safety assignment seeding.';
        RAISE NOTICE 'Please create safety.official@city.gov in Supabase Auth, promote with';
        RAISE NOTICE 'is_safety_officer=true, then re-run seed.sql.';
        RAISE NOTICE '====================================================================';
    ELSIF v_citizen_id IS NOT NULL THEN
        RAISE NOTICE 'Seeding demo safety assignment using designated safety officer ID: %', v_safety_official_id;

        -- Assignment 3: Safety Complaint Assignment (Unlit Walkway -> Electrical Unit A)
        INSERT INTO public.assignments (
            id, complaint_id, hotspot_id, worker_id, officer_id, task_description, status, created_at, updated_at
        ) VALUES (
            '40404040-0003-0000-0000-000000000001',
            '10101010-0004-0000-0000-000000000003', -- Unlit walkway near hostel
            NULL,
            'cccccccc-3333-0000-0000-000000000001', -- Electrical Streetlight Unit A
            v_safety_official_id,
            'Replace burned-out underground feeder cable and install 100W LED fixtures along park walkway.',
            'Assigned',
            now() - INTERVAL '30 minutes',
            now() - INTERVAL '30 minutes'
        ) ON CONFLICT (id) DO UPDATE SET
            task_description = EXCLUDED.task_description,
            status = EXCLUDED.status;

    END IF;

    RAISE NOTICE 'Seed script execution completed successfully.';
END $$;
-- ==============================================================================
