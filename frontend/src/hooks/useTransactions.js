import { useQuery } from "@tanstack/react-query";
import { fetchTransactions } from "../services/api";

export const useTransactions = (filters, appliedDateRange) => {
  return useQuery({
    queryKey: ["transactions", filters, appliedDateRange],
    queryFn: () => fetchTransactions({ ...filters, ...appliedDateRange }),
    keepPreviousData: true,
    // Only fetch when we have an appliedDateRange
    enabled: !!appliedDateRange.startDate && !!appliedDateRange.endDate,
  });
};
