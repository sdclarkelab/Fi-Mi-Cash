import React, { useCallback } from "react";
import DatePicker from "react-datepicker";
import { HiRefresh, HiExclamationCircle } from "react-icons/hi";
import { useDateRange } from "../context/DateRangeContext";
import "react-datepicker/dist/react-datepicker.css";

const DateRangePicker = () => {
  const { 
    dateRange, 
    setDateRange, 
    setAppliedDateRange, 
    validationError,
    clearValidationError 
  } = useDateRange();

  const handleStartDateChange = useCallback((date) => {
    clearValidationError();
    setDateRange({ ...dateRange, startDate: date });
  }, [dateRange, setDateRange, clearValidationError]);

  const handleEndDateChange = useCallback((date) => {
    clearValidationError();
    setDateRange({ ...dateRange, endDate: date });
  }, [dateRange, setDateRange, clearValidationError]);

  const handleApplyFilter = useCallback(() => {
    const success = setAppliedDateRange(dateRange);
    if (!success) {
      // Error will be shown via validationError state
      return;
    }
  }, [dateRange, setAppliedDateRange]);

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col sm:flex-row gap-4 items-end">
        <div className="flex gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Start Date
            </label>
            <DatePicker
              selected={dateRange.startDate}
              onChange={handleStartDateChange}
              className={`block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm ${
                validationError ? 'border-red-300' : 'border-gray-300'
              }`}
              maxDate={dateRange.endDate}
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              End Date
            </label>
            <DatePicker
              selected={dateRange.endDate}
              onChange={handleEndDateChange}
              className={`block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm ${
                validationError ? 'border-red-300' : 'border-gray-300'
              }`}
              minDate={dateRange.startDate}
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
      
      {validationError && (
        <div className="flex items-center gap-2 text-red-600 text-sm bg-red-50 p-3 rounded-md border border-red-200">
          <HiExclamationCircle className="w-4 h-4 flex-shrink-0" />
          <span>{validationError}</span>
        </div>
      )}
    </div>
  );
};

export default DateRangePicker;
