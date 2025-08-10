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

  const cardTypes = summary.by_card_type || {};
  const hasCardTypes = Object.keys(cardTypes).length > 0;

  return (
    <div className="mt-8 space-y-5">
      <div className="grid grid-cols-1 gap-5 sm:grid-cols-2">
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
      </div>
      
      {hasCardTypes && (
        <div>
          <h3 className="text-lg font-medium text-gray-900 mb-3">Spending by Card</h3>
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {Object.entries(cardTypes).map(([cardType, data]) => (
              <div key={cardType} className="bg-white overflow-hidden shadow rounded-lg">
                <div className="px-4 py-5 sm:p-6">
                  <dt className="text-sm font-medium text-gray-500 truncate">
                    {cardType} JMD
                  </dt>
                  <dd className="mt-1 text-2xl font-semibold text-gray-900">
                    {formatCurrency(data.total)}
                  </dd>
                  <p className="mt-1 text-xs text-gray-400">
                    {data.count} transactions
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default TransactionSummary;
