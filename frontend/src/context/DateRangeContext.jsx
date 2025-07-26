import React, { createContext, useContext, useState, useCallback } from "react";
import { isValid, isAfter, isBefore, startOfDay } from "date-fns";

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

// Validation function for date ranges
const validateDateRange = (startDate, endDate) => {
  if (!startDate || !endDate) {
    return { isValid: false, error: "Both start and end dates are required" };
  }
  
  if (!isValid(startDate) || !isValid(endDate)) {
    return { isValid: false, error: "Invalid date provided" };
  }
  
  if (isAfter(startDate, endDate)) {
    return { isValid: false, error: "Start date cannot be after end date" };
  }
  
  // Check if date range is too far in the future (more than 1 year)
  const oneYearFromNow = new Date();
  oneYearFromNow.setFullYear(oneYearFromNow.getFullYear() + 1);
  
  if (isAfter(startDate, oneYearFromNow)) {
    return { isValid: false, error: "Start date cannot be more than 1 year in the future" };
  }
  
  return { isValid: true, error: null };
};

export const DateRangeProvider = ({ children }) => {
  const [dateRange, setDateRange] = useState({
    startDate: getStartDate(),
    endDate: new Date(),
  });

  const [appliedDateRange, setAppliedDateRange] = useState({
    startDate: getStartDate(),
    endDate: new Date(),
  });

  const [validationError, setValidationError] = useState(null);

  // Safe date range setter with validation
  const setDateRangeWithValidation = useCallback((newRange) => {
    const { startDate, endDate } = newRange;
    const validation = validateDateRange(startDate, endDate);
    
    if (!validation.isValid) {
      setValidationError(validation.error);
      return false;
    }
    
    setValidationError(null);
    // Create new date objects to avoid mutation
    setDateRange({
      startDate: startOfDay(new Date(startDate)),
      endDate: startOfDay(new Date(endDate))
    });
    
    return true;
  }, []);

  // Safe applied date range setter with validation
  const setAppliedDateRangeWithValidation = useCallback((newRange) => {
    const { startDate, endDate } = newRange;
    const validation = validateDateRange(startDate, endDate);
    
    if (!validation.isValid) {
      setValidationError(validation.error);
      return false;
    }
    
    setValidationError(null);
    // Create new date objects to avoid mutation
    setAppliedDateRange({
      startDate: startOfDay(new Date(startDate)),
      endDate: startOfDay(new Date(endDate))
    });
    
    return true;
  }, []);

  return (
    <DateRangeContext.Provider
      value={{
        dateRange,
        setDateRange: setDateRangeWithValidation,
        appliedDateRange,
        setAppliedDateRange: setAppliedDateRangeWithValidation,
        validationError,
        clearValidationError: () => setValidationError(null),
      }}
    >
      {children}
    </DateRangeContext.Provider>
  );
};

export const useDateRange = () => {
  const context = useContext(DateRangeContext);
  
  if (!context) {
    throw new Error(
      'useDateRange must be used within a DateRangeProvider. ' +
      'Make sure to wrap your component tree with <DateRangeProvider>.'
    );
  }
  
  return context;
};
