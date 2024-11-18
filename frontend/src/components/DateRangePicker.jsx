import React from "react";
import DatePicker from "react-datepicker";
import { useDateRange } from "../context/DateRangeContext";
import "react-datepicker/dist/react-datepicker.css";

const DateRangePicker = () => {
  const { dateRange, setDateRange } = useDateRange();

  return (
    <div className="flex gap-4 items-center">
      <div>
        <label className="block text-sm font-medium text-gray-700">
          Start Date
        </label>
        <DatePicker
          selected={dateRange.startDate}
          onChange={(date) => setDateRange({ ...dateRange, startDate: date })}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
        />
      </div>
      <div>
        <label className="block text-sm font-medium text-gray-700">
          End Date
        </label>
        <DatePicker
          selected={dateRange.endDate}
          onChange={(date) => setDateRange({ ...dateRange, endDate: date })}
          className="mt-1 block w-full rounded-md border-gray-300 shadow-sm"
        />
      </div>
    </div>
  );
};

export default DateRangePicker;
