import axios from "axios";

const API_BASE_URL =
  process.env.REACT_APP_API_BASE_URL || "http://localhost:8000/api/v1";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    "Content-Type": "application/json",
  },
});

// Add response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const errorMessage =
      error.response?.data?.detail || "An unexpected error occurred";
    console.error("API Error:", errorMessage);
    throw new Error(errorMessage);
  }
);

export const fetchTransactions = async ({
  startDate,
  endDate,
  category,
  subcategory,
  minConfidence = 0.0,
}) => {
  try {
    const params = new URLSearchParams();
    if (startDate instanceof Date)
      params.append("startDate", startDate.toISOString());
    if (endDate instanceof Date)
      params.append("endDate", endDate.toISOString());
    if (category) params.append("category", category);
    if (subcategory) params.append("subcategory", subcategory);
    if (typeof minConfidence === "number")
      params.append("min_confidence", minConfidence.toString());

    const { data } = await api.get(`/transactions?${params.toString()}`);
    return data;
  } catch (error) {
    throw new Error(`Failed to fetch transactions: ${error.message}`);
  }
};

export const toggleTransactionExclusion = async (transactionId, excluded) => {
  try {
    const { data } = await api.patch(
      `/transactions/${transactionId}/toggle-exclude`,
      {
        excluded: excluded,
      }
    );
    return data;
  } catch (error) {
    throw new Error(`Failed to toggle transaction exclusion: ${error.message}`);
  }
};
