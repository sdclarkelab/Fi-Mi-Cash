import { useQuery } from "@tanstack/react-query";
import { fetchTransactions } from "../services/api";

// Using a consistent transaction query key across components
export const transactionQueryKey = (filters, dateRange, pagination) => [
  "transactions",
  filters,
  dateRange,
  pagination,
];

export const useTransactionData = (filters, appliedDateRange) => {
  return useQuery({
    queryKey: transactionQueryKey(filters, appliedDateRange),
    queryFn: () => fetchTransactions({ ...filters, ...appliedDateRange }),
    keepPreviousData: true,
    enabled: !!appliedDateRange.startDate && !!appliedDateRange.endDate,
  });
};
