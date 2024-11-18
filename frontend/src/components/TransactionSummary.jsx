import React from "react";
import { useSummary } from "../hooks/useSummary";
import { formatCurrency } from "../utils/formatters";
import { useDateRange } from "../context/DateRangeContext";
import LoadingSpinner from "./LoadingSpinner";

const TransactionSummary = () => {
  const { dateRange } = useDateRange();
  const { data: summary, isLoading, error } = useSummary(dateRange);

  if (isLoading) return <LoadingSpinner />;
  if (error) return <div>Error loading summary</div>;

  return (
    <div className="mt-8 grid grid-cols-1 gap-5 sm:grid-cols-3">
      <div className="bg-white overflow-hidden shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <dt className="text-sm font-medium text-gray-500 truncate">
            Total Spending
          </dt>
          <dd className="mt-1 text-3xl font-semibold text-gray-900">
            {formatCurrency(summary.total_spending)}
          </dd>
        </div>
      </div>
      <div className="bg-white overflow-hidden shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <dt className="text-sm font-medium text-gray-500 truncate">
            Transaction Count
          </dt>
          <dd className="mt-1 text-3xl font-semibold text-gray-900">
            {summary.transaction_count}
          </dd>
        </div>
      </div>
      <div className="bg-white overflow-hidden shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <dt className="text-sm font-medium text-gray-500 truncate">
            Average Transaction
          </dt>
          <dd className="mt-1 text-3xl font-semibold text-gray-900">
            {formatCurrency(summary.average_transaction)}
          </dd>
        </div>
      </div>
    </div>
  );
};

export default TransactionSummary;
