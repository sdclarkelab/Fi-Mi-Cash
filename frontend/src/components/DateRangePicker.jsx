import React from "react";
import DatePicker from "react-datepicker";
import { HiRefresh } from "react-icons/hi";
import { useDateRange } from "../context/DateRangeContext";
import "react-datepicker/dist/react-datepicker.css";

const DateRangePicker = () => {
  const { dateRange, setDateRange, setAppliedDateRange } = useDateRange();

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
