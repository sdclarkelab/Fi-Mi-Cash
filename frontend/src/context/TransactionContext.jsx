import React, { createContext, useContext, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchTransactions } from "../services/api";
import { transactionQueryKey } from "../hooks/useTransactionData";

const TransactionContext = createContext();

export const TransactionProvider = ({ children }) => {
  // Set default date range (last 30 days)
  const endDate = new Date();
  const startDate = new Date();
  startDate.setDate(startDate.getDate() - 30);

  const [filters, setFilters] = useState({
    category: null,
    subcategory: null,
    startDate: startDate,
    endDate: endDate,
  });

  // Fetch transaction data to be shared across components
  const {
    data: transactionData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: transactionQueryKey(filters, {
      startDate: filters.startDate,
      endDate: filters.endDate,
    }),
    queryFn: () =>
      fetchTransactions({
        ...filters,
        startDate: filters.startDate,
        endDate: filters.endDate,
      }),
    keepPreviousData: true,
    enabled: !!filters.startDate && !!filters.endDate,
  });

  const updateFilters = (category, subcategory = null) => {
    setFilters((prev) => ({
      ...prev,
      category,
      subcategory,
    }));
  };

  const updateDateRange = (startDate, endDate) => {
    setFilters((prev) => ({
      ...prev,
      startDate,
      endDate,
    }));
  };

  return (
    <TransactionContext.Provider
      value={{
        filters,
        updateFilters,
        updateDateRange,
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
