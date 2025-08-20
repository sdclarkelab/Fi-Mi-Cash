import React, { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DateRangeProvider } from "./context/DateRangeContext";
import { TransactionProvider, useTransactionContext } from "./context/TransactionContext";
import ErrorBoundary from "./components/ErrorBoundary";
import Header from "./components/Header";
import DateRangePicker from "./components/DateRangePicker";
import TransactionList from "./components/TransactionList";
import TransactionSummary from "./components/TransactionSummary";
import CategoryFilter from "./components/CategoryFilter";
import AddTransactionModal from "./components/AddTransactionModal";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 2,
      staleTime: 30000,
    },
  },
});

const AppContent = () => {
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const { transactionData, refetch } = useTransactionContext();

  const categories = transactionData?.categories || {};

  return (
    <div className="min-h-screen bg-gray-100">
      <Header />
      <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
        <div className="relative z-10 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
          <DateRangePicker />
          <div className="flex gap-2">
            <CategoryFilter />
            <button
              onClick={() => setIsAddModalOpen(true)}
              className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md text-sm font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              Add Transaction
            </button>
          </div>
        </div>

        <div className="space-y-6">
          <ErrorBoundary>
            <TransactionSummary />
          </ErrorBoundary>
          <ErrorBoundary>
            <TransactionList />
          </ErrorBoundary>
        </div>
      </main>
      
      <AddTransactionModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        categories={categories}
        onSuccess={() => {
          refetch();
        }}
      />
    </div>
  );
};

const App = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary>
        <DateRangeProvider>
          <TransactionProvider>
            <AppContent />
          </TransactionProvider>
        </DateRangeProvider>
      </ErrorBoundary>
    </QueryClientProvider>
  );
};

export default App;
