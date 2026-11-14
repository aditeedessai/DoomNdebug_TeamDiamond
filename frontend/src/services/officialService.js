import api from "./api";

/**
 * Official & Worker Portal Service Layer
 * Interacts with FastAPI backend endpoints for municipal administration, triage, assignments, and safety management.
 */
const officialService = {
  // =========================================================================
  // 1. DASHBOARD & ANALYTICS
  // =========================================================================

  /**
   * Retrieve role-discriminated dashboard summary.
   * Calls: GET /api/v1/dashboard/summary
   */
  getDashboardSummary: async (params = {}) => {
    const response = await api.get("/dashboard/summary", { params });
    return response.data;
  },

  /**
   * Retrieve department-level performance metrics and resolution rates.
   * Calls: GET /api/v1/dashboard/departments
   */
  getDepartmentStats: async (params = {}) => {
    const response = await api.get("/dashboard/departments", { params });
    return response.data;
  },

  /**
   * Retrieve priority distribution (Critical, High, Medium, Low).
   * Calls: GET /api/v1/dashboard/priorities
   */
  getPriorityBreakdown: async (params = {}) => {
    const response = await api.get("/dashboard/priorities", { params });
    return response.data;
  },

  /**
   * Retrieve safety incident dashboard metrics (Safety officers only).
   * Calls: GET /api/v1/dashboard/safety
   */
  getSafetyDashboard: async () => {
    const response = await api.get("/dashboard/safety");
    return response.data;
  },

  // =========================================================================
  // 2. COMPLAINT MANAGEMENT
  // =========================================================================

  /**
   * List complaints within official's authorized scope.
   * Calls: GET /api/v1/complaints
   */
  getComplaints: async (params = {}) => {
    const response = await api.get("/complaints", { params });
    return response.data;
  },

  /**
   * Retrieve single complaint detail with updates timeline and duplicate suggestions.
   * Calls: GET /api/v1/complaints/{id}
   */
  getComplaintById: async (id) => {
    const response = await api.get(`/complaints/${id}`);
    return response.data;
  },

  /**
   * Update complaint lifecycle status, priority, or remarks.
   * Calls: PATCH /api/v1/complaints/{id}/status
   */
  updateComplaintStatus: async (id, statusData) => {
    const response = await api.patch(`/complaints/${id}/status`, statusData);
    return response.data;
  },

  /**
   * Assign or reassign complaint to a municipal department.
   * Calls: POST /api/v1/complaints/{id}/assign
   */
  assignComplaint: async (id, assignData) => {
    const response = await api.post(`/complaints/${id}/assign`, assignData);
    return response.data;
  },

  /**
   * Retrieve complaint status update history.
   * Calls: GET /api/v1/complaints/{id}/updates
   */
  getComplaintTimeline: async (id) => {
    const response = await api.get(`/complaints/${id}/updates`);
    return response.data;
  },

  /**
   * Link an active complaint as duplicate of a master incident.
   * Calls: POST /api/v1/complaints/{id}/link-duplicate
   */
  linkDuplicateComplaint: async (id, masterId) => {
    const response = await api.post(`/complaints/${id}/link-duplicate`, { master_id: masterId });
    return response.data;
  },

  // =========================================================================
  // 3. PROJECTS & CITIZEN FEEDBACK
  // =========================================================================

  /**
   * List municipal projects.
   * Calls: GET /api/v1/projects
   */
  getProjects: async (params = {}) => {
    const response = await api.get("/projects", { params });
    return response.data;
  },

  /**
   * Create a new municipal infrastructure project.
   * Calls: POST /api/v1/projects
   */
  createProject: async (projectData) => {
    const response = await api.post("/projects", projectData);
    return response.data;
  },

  /**
   * Update project details or publication status.
   * Calls: PATCH /api/v1/projects/{id}
   */
  updateProject: async (id, projectData) => {
    const response = await api.patch(`/projects/${id}`, projectData);
    return response.data;
  },

  /**
   * List submitted citizen feedback on municipal projects.
   * Calls: GET /api/v1/feedback
   */
  getFeedback: async (params = {}) => {
    const response = await api.get("/feedback", { params });
    return response.data;
  },

  /**
   * Convert actionable feedback into a tracked complaint.
   * Calls: POST /api/v1/feedback/{id}/convert-to-complaint
   */
  convertFeedbackToComplaint: async (id, data = {}) => {
    const response = await api.post(`/feedback/${id}/convert-to-complaint`, data);
    return response.data;
  },

  // =========================================================================
  // 4. WORKERS & TASK ASSIGNMENTS
  // =========================================================================

  /**
   * List field workers within official's department or city.
   * Calls: GET /api/v1/workers
   */
  getWorkers: async (params = {}) => {
    const response = await api.get("/workers", { params });
    return response.data;
  },

  /**
   * Retrieve worker details and active assignments.
   * Calls: GET /api/v1/workers/{worker_id}
   */
  getWorkerById: async (id) => {
    const response = await api.get(`/workers/${id}`);
    return response.data;
  },

  /**
   * List task assignments.
   * Calls: GET /api/v1/assignments
   */
  getAssignments: async (params = {}) => {
    const response = await api.get("/assignments", { params });
    return response.data;
  },

  /**
   * Retrieve assignment details.
   * Calls: GET /api/v1/assignments/{id}
   */
  getAssignmentById: async (id) => {
    const response = await api.get(`/assignments/${id}`);
    return response.data;
  },

  /**
   * Create an assignment targeting a complaint or traffic hotspot.
   * Calls: POST /api/v1/assignments
   */
  createAssignment: async (assignmentData) => {
    const response = await api.post("/assignments", assignmentData);
    return response.data;
  },

  /**
   * Update assignment status, progress notes, or reassignment.
   * Calls: PATCH /api/v1/assignments/{id}
   */
  updateAssignment: async (id, updateData) => {
    const response = await api.patch(`/assignments/${id}`, updateData);
    return response.data;
  },

  // =========================================================================
  // 5. SAFETY REGISTER (Safety Officers only)
  // =========================================================================

  /**
   * List restricted safety reports register.
   * Calls: GET /api/v1/safety-reports
   */
  getSafetyReports: async (params = {}) => {
    const response = await api.get("/safety-reports", { params });
    return response.data;
  },

  /**
   * Retrieve safety report investigation detail.
   * Calls: GET /api/v1/safety-reports/{id}
   */
  getSafetyReportById: async (id) => {
    const response = await api.get(`/safety-reports/${id}`);
    return response.data;
  },

  /**
   * Update safety report investigation notes, status, or department.
   * Calls: PATCH /api/v1/safety-reports/{id}
   */
  updateSafetyReport: async (id, updateData) => {
    const response = await api.patch(`/safety-reports/${id}`, updateData);
    return response.data;
  },

  // =========================================================================
  // 6. OFFICIAL MAP & HOTSPOTS
  // =========================================================================

  /**
   * Retrieve map complaints.
   * Calls: GET /api/v1/map/complaints
   */
  getMapComplaints: async (params = {}) => {
    const response = await api.get("/map/complaints", { params });
    return response.data;
  },

  /**
   * Retrieve map projects.
   * Calls: GET /api/v1/map/projects
   */
  getMapProjects: async (params = {}) => {
    const response = await api.get("/map/projects", { params });
    return response.data;
  },

  /**
   * Retrieve traffic hotspots.
   * Calls: GET /api/v1/map/hotspots
   */
  getMapHotspots: async (params = {}) => {
    const response = await api.get("/map/hotspots", { params });
    return response.data;
  },

  /**
   * Create demo traffic hotspot.
   * Calls: POST /api/v1/map/hotspots
   */
  createMapHotspot: async (hotspotData) => {
    const response = await api.post("/map/hotspots", hotspotData);
    return response.data;
  },

  /**
   * Retrieve safety zones or officer incident markers.
   * Calls: GET /api/v1/map/safety-zones
   */
  getMapSafetyZones: async () => {
    const response = await api.get("/map/safety-zones");
    return response.data;
  },
};

export default officialService;
