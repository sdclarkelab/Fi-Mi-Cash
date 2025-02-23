import React, { createContext, useContext, useState } from "react";

const TransactionContext = createContext();

export const TransactionProvider = ({ children }) => {
  const [filters, setFilters] = useState({
    category: null,
    subcategory: null,
  });

  const updateFilters = (category, subcategory = null) => {
    setFilters({ category, subcategory });
  };

  return (
    <TransactionContext.Provider value={{ filters, updateFilters }}>
      {children}
    </TransactionContext.Provider>
  );
};

export const useTransactionContext = () => useContext(TransactionContext);
