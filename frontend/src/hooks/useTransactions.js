import { useQuery } from "@tanstack/react-query";
import { fetchTransactions } from "../services/api";

export const useTransactions = (filters) => {
  return useQuery({
    queryKey: ["transactions", filters],
    queryFn: () => fetchTransactions(filters),
    keepPreviousData: true,
    staleTime: 30000, // Consider data fresh for 30 seconds
    retry: 2, // Retry failed requests twice
    refetchOnWindowFocus: false, // Don't refetch on window focus
  });
};
