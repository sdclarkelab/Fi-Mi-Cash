import { useQuery } from "@tanstack/react-query";
import { fetchSummary } from "../services/api";

export const useSummary = (filters) => {
  return useQuery({
    queryKey: ["summary", filters],
    queryFn: () => fetchSummary(filters),
  });
};
