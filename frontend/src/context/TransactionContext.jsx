import React, { createContext, useContext, useState } from "react";

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
      }}
    >
      {children}
    </TransactionContext.Provider>
  );
};

export const useTransactionContext = () => useContext(TransactionContext);
