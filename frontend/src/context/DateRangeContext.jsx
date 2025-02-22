import React, { createContext, useContext, useState } from "react";

const DateRangeContext = createContext();

function getStartDate() {
  const today = new Date();
  const day = today.getDate();
  // If the day is less than 25, pick the 25th of the previous month
  // Otherwise, pick the 25th of the current month
  if (day < 25) {
    return new Date(today.getFullYear(), today.getMonth() - 1, 25);
  } else {
    return new Date(today.getFullYear(), today.getMonth(), 25);
  }
}

export const DateRangeProvider = ({ children }) => {
  const [dateRange, setDateRange] = useState({
    startDate: getStartDate(),
    endDate: new Date(),
  });

  const [appliedDateRange, setAppliedDateRange] = useState({
    startDate: getStartDate(),
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
