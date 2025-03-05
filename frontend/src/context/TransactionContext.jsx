import React, { createContext, useContext, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchTransactions } from "../services/api";
import { transactionQueryKey } from "../hooks/useTransactionData";
import { useDateRange } from "./DateRangeContext";

const TransactionContext = createContext();

export const TransactionProvider = ({ children }) => {
  // Use category filters only, date range comes from DateRangeContext
  const [filters, setFilters] = useState({
    category: null,
    subcategory: null,
  });

  // Get date range from DateRangeContext
  const { appliedDateRange } = useDateRange();

  // Fetch transaction data to be shared across components
  const {
    data: transactionData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: transactionQueryKey(filters, appliedDateRange),
    queryFn: () =>
      fetchTransactions({
        ...filters,
        startDate: appliedDateRange.startDate,
        endDate: appliedDateRange.endDate,
      }),
    keepPreviousData: true,
    enabled: !!appliedDateRange.startDate && !!appliedDateRange.endDate,
  });

  const updateFilters = (category, subcategory = null) => {
    setFilters((prev) => ({
      ...prev,
      category,
      subcategory,
    }));
  };

  return (
    <TransactionContext.Provider
      value={{
        filters,
        updateFilters,
        transactionData,
        isLoading,
        error,
        refetch,
      }}
    >
      {children}
    </TransactionContext.Provider>
  );
};

export const useTransactionContext = () => useContext(TransactionContext);
