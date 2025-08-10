import React, { createContext, useContext, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchTransactions, getTransactionCount } from "../services/api";
import { transactionQueryKey } from "../hooks/useTransactionData";
import { useDateRange } from "./DateRangeContext";

const TransactionContext = createContext();

export const TransactionProvider = ({ children }) => {
  // Use category filters only, date range comes from DateRangeContext
  const [filters, setFilters] = useState({
    categories: [], // Array of {category, subcategory} objects for multi-select
  });

  // Pagination state
  const [pagination, setPagination] = useState({
    limit: 100,
    offset: 0,
    currentPage: 1,
  });

  // Get date range from DateRangeContext
  const { appliedDateRange } = useDateRange();

  // Fetch transaction count for pagination
  const {
    data: totalCount = 0,
    isLoading: isCountLoading,
  } = useQuery({
    queryKey: ["transactionCount", filters, appliedDateRange],
    queryFn: () =>
      getTransactionCount({
        ...filters,
        startDate: appliedDateRange.startDate,
        endDate: appliedDateRange.endDate,
      }),
    enabled: !!appliedDateRange.startDate && !!appliedDateRange.endDate,
  });

  // Fetch transaction data to be shared across components
  const {
    data: transactionData,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: transactionQueryKey(filters, appliedDateRange, pagination),
    queryFn: () =>
      fetchTransactions({
        ...filters,
        startDate: appliedDateRange.startDate,
        endDate: appliedDateRange.endDate,
        limit: pagination.limit,
        offset: pagination.offset,
      }),
    keepPreviousData: true,
    enabled: !!appliedDateRange.startDate && !!appliedDateRange.endDate,
  });

  const updateFilters = (categories) => {
    setFilters((prev) => ({
      ...prev,
      categories,
    }));
    // Reset pagination when filters change
    setPagination(prev => ({
      ...prev,
      offset: 0,
      currentPage: 1,
    }));
  };

  const updatePagination = (newPagination) => {
    setPagination(prev => ({
      ...prev,
      ...newPagination,
    }));
  };

  const goToPage = (page) => {
    const newOffset = (page - 1) * pagination.limit;
    setPagination(prev => ({
      ...prev,
      offset: newOffset,
      currentPage: page,
    }));
  };

  return (
    <TransactionContext.Provider
      value={{
        filters,
        updateFilters,
        transactionData,
        isLoading: isLoading || isCountLoading,
        error,
        refetch,
        pagination,
        updatePagination,
        goToPage,
        totalCount,
      }}
    >
      {children}
    </TransactionContext.Provider>
  );
};

export const useTransactionContext = () => useContext(TransactionContext);
