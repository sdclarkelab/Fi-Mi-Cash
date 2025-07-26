import { useQuery } from "@tanstack/react-query";
import { fetchTransactions } from "../services/api";

export const useTransactions = (filters, appliedDateRange, pagination = { limit: 100, offset: 0 }) => {
  return useQuery({
    queryKey: ["transactions", filters, appliedDateRange, pagination],
    queryFn: () => fetchTransactions({ 
      ...filters, 
      ...appliedDateRange, 
      limit: pagination.limit,
      offset: pagination.offset 
    }),
    keepPreviousData: true,
    // Only fetch when we have an appliedDateRange
    enabled: !!appliedDateRange.startDate && !!appliedDateRange.endDate,
  });
};
