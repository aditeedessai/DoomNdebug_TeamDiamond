import api from "./api";

const authService = {
  /**
   * Authenticate user with email and password.
   * @param {string} email
   * @param {string} password
   * @returns {Promise<{ session: object, profile: object, message: string }>}
   */
  login: async (email, password) => {
    const response = await api.post("/auth/login", { email, password });
    return response.data;
  },

  /**
   * Register a new citizen account.
   * @param {{ email: string, password: string, full_name: string, phone?: string }} userData
   * @returns {Promise<{ session?: object, profile: object, message: string }>}
   */
  register: async (userData) => {
    const response = await api.post("/auth/register", userData);
    return response.data;
  },

  /**
   * Retrieve current authenticated user profile.
   * @returns {Promise<{ id: string, full_name: string, phone?: string, role: string, department_id?: string, is_safety_officer: boolean }>}
   */
  getProfile: async () => {
    const response = await api.get("/auth/me");
    return response.data;
  },

  /**
   * Log out user and clear stored authentication state.
   */
  logout: () => {
    localStorage.removeItem("access_token");
  },
};

export default authService;

