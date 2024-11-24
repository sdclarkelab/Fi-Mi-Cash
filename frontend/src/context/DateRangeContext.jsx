import React, { createContext, useContext, useState } from "react";

const DateRangeContext = createContext();

export const DateRangeProvider = ({ children }) => {
  const [dateRange, setDateRange] = useState({
    startDate: new Date(new Date().setMonth(new Date().getMonth() - 1)),
    endDate: new Date(),
  });

  // Add appliedDateRange to track the actually applied filter
  const [appliedDateRange, setAppliedDateRange] = useState({
    startDate: new Date(new Date().setMonth(new Date().getMonth() - 1)),
    endDate: new Date(),
  });

  return (
    <DateRangeContext.Provider
      value={{
        dateRange,
        setDateRange,
        appliedDateRange,
        setAppliedDateRange,
      }}
    >
      {children}
    </DateRangeContext.Provider>
  );
};

export const useDateRange = () => useContext(DateRangeContext);
