-- ==============================================================================
-- AI City Management Platform — Supabase Seed Data
-- Task: M4-02 Supabase Database & Authentication
-- Author: Member 4 (Backend, Database & Integration Lead)
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
-- 5. ADMINISTRATIVE INSTRUCTIONS FOR OFFICIAL & WORKER ACCOUNTS
-- ==============================================================================
-- To provision official and worker demo accounts in Supabase:
--
-- 1. Create the user in Supabase Auth Dashboard (or via admin API):
--    - Official User: official@city.gov / Password123!
--    - Safety Officer: safety.official@city.gov / Password123!
--    - Worker User: worker@city.gov / Password123!
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
--        department_id = '11111111-1111-1111-1111-111111111111',
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
-- ==============================================================================

