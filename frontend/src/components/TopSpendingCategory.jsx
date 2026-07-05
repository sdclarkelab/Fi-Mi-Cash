import React from "react";
import { formatCurrency } from "../utils/formatters";
import { useTransactionContext } from "../context/TransactionContext";
import LoadingSpinner from "./LoadingSpinner";
import ErrorAlert from "./ErrorAlert";

const TopSpendingCategory = () => {
  const { transactionData, isLoading, error, refetch } =
    useTransactionContext();

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorAlert error={error} onRetry={refetch} />;

  const summary = transactionData?.transaction_summary;
  
  // Handle edge cases: no summary, no category, or zero amount
  if (!summary) return null;
  
  const hasTopCategory = summary.top_spending_category && 
                        summary.top_spending_category_amount && 
                        summary.top_spending_category_amount > 0;

  if (!hasTopCategory) {
    return (
      <div className="bg-white overflow-hidden shadow rounded-lg">
        <div className="px-4 py-5 sm:p-6">
          <dt className="text-sm font-medium text-gray-500 truncate">
            Top Spending Category
          </dt>
          <dd className="mt-1 text-2xl font-semibold text-gray-400">
            No Data
          </dd>
          <p className="mt-1 text-sm text-gray-400">
            No transactions in selected period
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white overflow-hidden shadow rounded-lg">
      <div className="px-4 py-5 sm:p-6">
        <dt className="text-sm font-medium text-gray-500 truncate">
          Top Spending Category
        </dt>
        <dd className="mt-1 text-2xl font-semibold text-gray-900 truncate" title={summary.top_spending_category}>
          {summary.top_spending_category}
        </dd>
        <p className="mt-1 text-lg text-gray-600">
          {formatCurrency(summary.top_spending_category_amount)}
        </p>
      </div>
    </div>
  );
};

export default TopSpendingCategory;