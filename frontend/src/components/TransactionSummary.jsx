import React from "react";
import { formatCurrency } from "../utils/formatters";
import { useTransactionContext } from "../context/TransactionContext";
import LoadingSpinner from "./LoadingSpinner";
import ErrorAlert from "./ErrorAlert";

const TransactionSummary = () => {
  const { transactionData, isLoading, error, refetch } =
    useTransactionContext();

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorAlert error={error} onRetry={refetch} />;

  const summary = transactionData?.transaction_summary;
  if (!summary) return null;

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
