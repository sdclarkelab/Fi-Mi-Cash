// src/context/DateRangeContext.jsx
import React, { createContext, useContext, useState } from 'react';

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
    <DateRangeContext.Provider value={{ 
      dateRange, 
      setDateRange, 
      appliedDateRange, 
      setAppliedDateRange 
    }}>
      {children}
    </DateRangeContext.Provider>
  );
};

export const useDateRange = () => useContext(DateRangeContext);

// src/components/DateRangePicker.jsx
import React from 'react';
import DatePicker from 'react-datepicker';
import { HiRefresh } from 'react-icons/hi';
import { useDateRange } from '../context/DateRangeContext';
import "react-datepicker/dist/react-datepicker.css";

const DateRangePicker = () => {
  const { 
    dateRange, 
    setDateRange, 
    setAppliedDateRange 
  } = useDateRange();

  const handleApplyFilter = () => {
    setAppliedDateRange(dateRange);
  };

  return (
    <div className="flex flex-col sm:flex-row gap-4 items-end">
      <div className="flex gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Start Date
          </label>
          <DatePicker
            selected={dateRange.startDate}
            onChange={(date) => setDateRange({ ...dateRange, startDate: date })}
            className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            End Date
          </label>
          <DatePicker
            selected={dateRange.endDate}
            onChange={(date) => setDateRange({ ...dateRange, endDate: date })}
            className="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
          />
        </div>
      </div>
      <div className="flex gap-2">
        <button
          onClick={handleApplyFilter}
          className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 transition-colors duration-200"
        >
          Apply Filter
        </button>
        <button
          onClick={handleApplyFilter}
          className="px-3 py-2 bg-gray-100 text-gray-600 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 transition-colors duration-200"
          title="Refresh"
        >
          <HiRefresh className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
};

export default DateRangePicker;

// src/hooks/useTransactions.js
import { useQuery } from '@tanstack/react-query';
import { fetchTransactions } from '../services/api';

export const useTransactions = (filters, appliedDateRange) => {
  return useQuery({
    queryKey: ['transactions', filters, appliedDateRange],
    queryFn: () => fetchTransactions({ ...filters, ...appliedDateRange }),
    keepPreviousData: true,
    // Only fetch when we have an appliedDateRange
    enabled: !!appliedDateRange.startDate && !!appliedDateRange.endDate,
  });
};

// src/hooks/useSummary.js
import { useQuery } from '@tanstack/react-query';
import { fetchSummary } from '../services/api';

export const useSummary = (filters, appliedDateRange) => {
  return useQuery({
    queryKey: ['summary', filters, appliedDateRange],
    queryFn: () => fetchSummary({ ...filters, ...appliedDateRange }),
    keepPreviousData: true,
    // Only fetch when we have an appliedDateRange
    enabled: !!appliedDateRange.startDate && !!appliedDateRange.endDate,
  });
};

// src/components/TransactionList.jsx
import React from 'react';
import { useTransactions } from '../hooks/useTransactions';
import { formatCurrency, formatDate } from '../utils/formatters';
import { useDateRange } from '../context/DateRangeContext';
import LoadingSpinner from './LoadingSpinner';
import ErrorAlert from './ErrorAlert';

const TransactionList = ({ category, subcategory }) => {
  const { appliedDateRange } = useDateRange();
  const { 
    data: transactions, 
    isLoading, 
    error,
    refetch
  } = useTransactions(
    { category, subcategory },
    appliedDateRange
  );

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorAlert error={error} onRetry={refetch} />;
  if (!transactions?.length) {
    return (
      <div className="text-center py-8 text-gray-500">
        No transactions found for the selected filters.
      </div>
    );
  }

  return (
    // ... rest of the component remains the same ...
  );
};

// src/components/TransactionSummary.jsx
const TransactionSummary = ({ category, subcategory }) => {
  const { appliedDateRange } = useDateRange();
  const { 
    data: summary, 
    isLoading, 
    error,
    refetch 
  } = useSummary(
    { category, subcategory },
    appliedDateRange
  );

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorAlert error={error} onRetry={refetch} />;

  return (
    // ... rest of the component remains the same ...
  );
};

// src/App.jsx - No changes needed to the structure, but make sure to use DateRangeProvider

export default App;
