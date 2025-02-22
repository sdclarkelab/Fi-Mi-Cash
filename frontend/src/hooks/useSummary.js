import { useQuery } from "@tanstack/react-query";
import { fetchSummary } from "../services/api";

export const useSummary = (filters, appliedDateRange) => {
  return useQuery({
    queryKey: ["summary", filters, appliedDateRange],
    queryFn: () => fetchSummary({ ...filters, ...appliedDateRange }),
    keepPreviousData: true,
    // Only fetch when we have an appliedDateRange
    enabled: !!appliedDateRange.startDate && !!appliedDateRange.endDate,
  });
};
