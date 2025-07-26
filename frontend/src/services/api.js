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
  limit = 100,
  offset = 0,
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
    if (typeof limit === "number")
      params.append("limit", limit.toString());
    if (typeof offset === "number")
      params.append("offset", offset.toString());

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

// Category Rules API functions
export const getAllRules = async () => {
  const response = await fetch(`${API_BASE_URL}/rules`);
  if (!response.ok) {
    throw new Error(`Failed to fetch rules: ${response.statusText}`);
  }
  return response.json();
};

export const addRule = async (merchant, category, subcategory) => {
  const response = await fetch(`${API_BASE_URL}/rules`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ merchant, category, subcategory }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to add rule");
  }

  return response.json();
};

export const updateRule = async (merchant, category, subcategory) => {
  const response = await fetch(`${API_BASE_URL}/rules`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ merchant, category, subcategory }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to update rule");
  }

  return response.json();
};

export const deleteRule = async (merchant) => {
  const response = await fetch(
    `${API_BASE_URL}/rules/${encodeURIComponent(merchant)}`,
    {
      method: "DELETE",
    }
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to delete rule");
  }

  return response.json();
};

export const getTransactionCount = async ({
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

    const { data } = await api.get(`/transactions/count?${params.toString()}`);
    return data.count;
  } catch (error) {
    throw new Error(`Failed to fetch transaction count: ${error.message}`);
  }
};
