
import api from "./api";

const citizenService = {
  getMyComplaints: async () => {
    const response = await api.get("/complaints/my");
    return response.data;
  },

  createComplaint: async (complaintData) => {
    const response = await api.post(
      "/complaints",
      complaintData
    );
    return response.data;
  },

  getProjects: async () => {
    const response = await api.get("/projects");
    return response.data;
  },

  submitFeedback: async (feedbackData) => {
    const response = await api.post(
      "/feedback",
      feedbackData
    );
    return response.data;
  },

  createSafetyReport: async (reportData) => {
    const response = await api.post(
      "/safety-reports",
      reportData
    );
    return response.data;
  },
};

export default citizenService;
