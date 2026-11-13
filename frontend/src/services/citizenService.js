import api from "./api";

const citizenService = {
  getMyComplaints: async (params = {}) => {
    const response = await api.get("/complaints/my", { params });
    return response.data;
  },

  getComplaintById: async (id) => {
    const response = await api.get(`/complaints/${id}`);
    return response.data;
  },

  createComplaint: async (complaintData) => {
    const response = await api.post(
      "/complaints",
      complaintData
    );
    return response.data;
  },

  updateComplaint: async (id, updateData) => {
    const response = await api.patch(
      `/complaints/${id}`,
      updateData
    );
    return response.data;
  },

  uploadImage: async (file) => {
    const formData = new FormData();
    formData.append("file", file);
    const response = await api.post("/complaints/upload-image", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });
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
