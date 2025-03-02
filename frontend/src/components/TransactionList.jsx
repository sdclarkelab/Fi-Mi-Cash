import React, { useState } from "react";
import { useTransactionData } from "../hooks/useTransactionData";
import { formatCurrency, formatDate } from "../utils/formatters";
import { useDateRange } from "../context/DateRangeContext";
import { useTransactionContext } from "../context/TransactionContext";
import LoadingSpinner from "./LoadingSpinner";
import ErrorAlert from "./ErrorAlert";
import { toggleTransactionExclusion as apiToggleExclusion } from "../services/api";

const TransactionList = () => {
  const { appliedDateRange } = useDateRange();
  const { filters } = useTransactionContext();
  const [updatingTransactionId, setUpdatingTransactionId] = useState(null);

  const { data, isLoading, error, isFetching, refetch } = useTransactionData(
    filters,
    appliedDateRange
  );

  const transactions = data?.transactions || [];

  const toggleTransactionExclusion = async (transactionId, currentExcluded) => {
    try {
      setUpdatingTransactionId(transactionId);
      await apiToggleExclusion(transactionId, !currentExcluded);
      await refetch();
    } catch (error) {
      console.error(error.message);
    } finally {
      setUpdatingTransactionId(null);
    }
  };

  if (isLoading) {
    return (
      <div className="mt-8 flex justify-center">
        <LoadingSpinner />
      </div>
    );
  }

  if (error) {
    return (
      <div className="mt-8">
        <ErrorAlert error={error} onRetry={refetch} />
      </div>
    );
  }

  if (!transactions?.length) {
    return (
      <div className="mt-8 text-center py-12 bg-white rounded-lg shadow">
        <svg
          className="mx-auto h-12 w-12 text-gray-400"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          aria-hidden="true"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={2}
            d="M9 13h6m-3-3v6m-9 1V7a2 2 0 012-2h6l2 2h6a2 2 0 012 2v8a2 2 0 01-2-2H5a2 2 0 01-2-2z"
          />
        </svg>
        <h3 className="mt-2 text-sm font-medium text-gray-900">
          No transactions found
        </h3>
        <p className="mt-1 text-sm text-gray-500">
          Try adjusting your filters to see more results.
        </p>
      </div>
    );
  }

  return (
    <div className="mt-8">
      <div className="relative">
        {/* Loading overlay for subsequent fetches */}
        {isFetching && !isLoading && (
          <div className="absolute inset-0 bg-white/50 flex items-center justify-center z-10">
            <LoadingSpinner />
          </div>
        )}

        {/* Table Header */}
        <div className="sm:flex sm:items-center mb-4">
          <div className="sm:flex-auto">
            <h2 className="text-lg font-semibold text-gray-900">
              Transactions
            </h2>
            <p className="mt-2 text-sm text-gray-700">
              Showing {transactions.length} transactions for the selected period
              {filters.category && ` in ${filters.category}`}
              {filters.subcategory && ` - ${filters.subcategory}`}.
            </p>
          </div>
        </div>

        {/* Transaction Table */}
        <div className="overflow-hidden shadow ring-1 ring-black ring-opacity-5 sm:rounded-lg">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-300">
              <thead className="bg-gray-50">
                <tr>
                  <th
                    scope="col"
                    className="py-3.5 pl-4 pr-3 text-left text-sm font-semibold text-gray-900 sm:pl-6"
                  >
                    Date
                  </th>
                  <th
                    scope="col"
                    className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900"
                  >
                    Merchant
                  </th>
                  <th
                    scope="col"
                    className="px-3 py-3.5 text-right text-sm font-semibold text-gray-900"
                  >
                    Amount
                  </th>
                  <th
                    scope="col"
                    className="px-3 py-3.5 text-left text-sm font-semibold text-gray-900"
                  >
                    Category
                  </th>
                  <th
                    scope="col"
                    className="px-3 py-3.5 text-center text-sm font-semibold text-gray-900"
                  >
                    Confidence
                  </th>
                  <th
                    scope="col"
                    className="px-3 py-3.5 text-center text-sm font-semibold text-gray-900"
                  >
                    Status
                  </th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 bg-white">
                {transactions.map((transaction) => (
                  <tr
                    key={transaction.id}
                    className="hover:bg-gray-50 transition-colors duration-150"
                  >
                    <td className="whitespace-nowrap py-4 pl-4 pr-3 text-sm text-gray-900 sm:pl-6">
                      {formatDate(transaction.date)}
                    </td>
                    <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-900">
                      {transaction.merchant}
                    </td>
                    <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-900 text-right font-medium">
                      {formatCurrency(transaction.amount)}
                    </td>
                    <td className="px-3 py-4 text-sm text-gray-900">
                      <div className="flex flex-col gap-1">
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                          {transaction.primary_category}
                        </span>
                        {transaction.subcategory && (
                          <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">
                            {transaction.subcategory}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="whitespace-nowrap px-3 py-4 text-sm text-gray-900">
                      <div className="flex items-center justify-center gap-2">
                        <div className="w-16 bg-gray-200 rounded-full h-2">
                          <div
                            className={`h-2 rounded-full ${
                              transaction.confidence >= 0.7
                                ? "bg-green-500"
                                : transaction.confidence >= 0.4
                                ? "bg-yellow-500"
                                : "bg-red-500"
                            }`}
                            style={{
                              width: `${transaction.confidence * 100}%`,
                            }}
                          />
                        </div>
                        <span className="text-xs text-gray-600">
                          {Math.round(transaction.confidence * 100)}%
                        </span>
                      </div>
                    </td>
                    <td className="whitespace-nowrap px-3 py-4 text-sm text-center">
                      <button
                        onClick={() =>
                          toggleTransactionExclusion(
                            transaction.id,
                            transaction.excluded
                          )
                        }
                        disabled={updatingTransactionId === transaction.id}
                        className={`px-3 py-1 rounded-md text-sm font-medium ${
                          transaction.excluded
                            ? "bg-red-100 text-red-800 hover:bg-red-200"
                            : "bg-green-100 text-green-800 hover:bg-green-200"
                        }`}
                      >
                        {updatingTransactionId === transaction.id ? (
                          <span className="inline-flex items-center">
                            <svg
                              className="animate-spin -ml-1 mr-2 h-4 w-4 text-current"
                              xmlns="http://www.w3.org/2000/svg"
                              fill="none"
                              viewBox="0 0 24 24"
                            >
                              <circle
                                className="opacity-25"
                                cx="12"
                                cy="12"
                                r="10"
                                stroke="currentColor"
                                strokeWidth="4"
                              ></circle>
                              <path
                                className="opacity-75"
                                fill="currentColor"
                                d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                              ></path>
                            </svg>
                            Updating...
                          </span>
                        ) : transaction.excluded ? (
                          "Excluded"
                        ) : (
                          "Include"
                        )}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default TransactionList;
