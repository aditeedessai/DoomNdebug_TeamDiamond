import api from "./api";

/**
 * Citizen Portal Service Layer
 * Interacts with FastAPI backend endpoints strictly adhering to backend Pydantic schemas.
 */
const citizenService = {
  /**
   * Retrieve role-discriminated dashboard metrics and recent complaints for authenticated citizen.
   * Calls: GET /api/v1/dashboard/summary
   */
  getDashboardSummary: async () => {
    const response = await api.get("/dashboard/summary");
    return response.data;
  },

  /**
   * Retrieve complaints submitted by the authenticated citizen.
   * Calls: GET /api/v1/complaints/my
   */
  getMyComplaints: async (params = {}) => {
    const response = await api.get("/complaints/my", { params });
    return response.data;
  },

  /**
   * Retrieve detailed complaint view including status update history.
   * Calls: GET /api/v1/complaints/{id}
   */
  getComplaintById: async (id) => {
    const response = await api.get(`/complaints/${id}`);
    return response.data;
  },

  /**
   * Submit a new civic complaint.
   * Calls: POST /api/v1/complaints
   * @param {{ title: string, description: string, latitude: number, longitude: number, category: string, issue_type: string, image_url?: string, safety_related?: boolean, safety_category?: string }} complaintData
   */
  createComplaint: async (complaintData) => {
    const response = await api.post("/complaints", complaintData);
    return response.data;
  },

  /**
   * Update complaint details by citizen owner (only allowed while Submitted or Needs More Information).
   * Calls: PATCH /api/v1/complaints/{id}
   */
  updateComplaint: async (id, updateData) => {
    const response = await api.patch(`/complaints/${id}`, updateData);
    return response.data;
  },

  /**
   * Upload an evidence image (JPEG, PNG, WebP <= 5 MB).
   * Calls: POST /api/v1/complaints/upload-image
   * @param {File} file
   * @returns {Promise<{ image_path: string, file_name: string, content_type: string, size_bytes: number, signed_url?: string }>}
   */
  uploadImage: async (file) => {
    const formData = new FormData();
    formData.append("file", file);
    const response = await api.post("/complaints/upload-image", formData);
    return response.data;
  },

  /**
   * Retrieve published municipal projects.
   * Calls: GET /api/v1/projects
   */
  getProjects: async (params = {}) => {
    const response = await api.get("/projects", { params });
    return response.data;
  },

  /**
   * Retrieve project details.
   * Calls: GET /api/v1/projects/{id}
   */
  getProjectById: async (id) => {
    const response = await api.get(`/projects/${id}`);
    return response.data;
  },

  /**
   * Submit citizen feedback on a municipal project.
   * Calls: POST /api/v1/feedback
   * @param {{ project_id: string, category: string, message: string }} feedbackData
   */
  submitFeedback: async (feedbackData) => {
    const response = await api.post("/feedback", feedbackData);
    return response.data;
  },

  /**
   * Retrieve map complaint markers (sanitized for citizens).
   * Calls: GET /api/v1/map/complaints
   */
  getMapComplaints: async (params = {}) => {
    const response = await api.get("/map/complaints", { params });
    return response.data;
  },

  /**
   * Retrieve map project markers (published projects only for citizens).
   * Calls: GET /api/v1/map/projects
   */
  getMapProjects: async (params = {}) => {
    const response = await api.get("/map/projects", { params });
    return response.data;
  },

  /**
   * Retrieve traffic congestion hotspot markers.
   * Calls: GET /api/v1/map/hotspots
   */
  getMapHotspots: async () => {
    const response = await api.get("/map/hotspots");
    return response.data;
  },

  /**
   * Retrieve privacy-preserving aggregated safety zones (rounded coordinates, 3+ reports).
   * Calls: GET /api/v1/map/safety-zones
   */
  getMapSafetyZones: async () => {
    const response = await api.get("/map/safety-zones");
    return response.data;
  },

  /**
   * Submit a safety infrastructure report.
   * Calls: POST /api/v1/safety-reports
   * @param {{ title?: string, description: string, latitude: number, longitude: number, safety_category: string, image_url?: string }} reportData
   */
  createSafetyReport: async (reportData) => {
    const response = await api.post("/safety-reports", reportData);
    return response.data;
  },

  /**
   * Retrieve safety reports submitted by the authenticated citizen.
   * Calls: GET /api/v1/safety-reports/mine
   */
  getMySafetyReports: async (params = {}) => {
    const response = await api.get("/safety-reports/mine", { params });
    return response.data;
  },
};

export default citizenService;
