import React from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DateRangeProvider } from "./context/DateRangeContext";
import { TransactionProvider } from "./context/TransactionContext";
import ErrorBoundary from "./components/ErrorBoundary";
import Header from "./components/Header";
import DateRangePicker from "./components/DateRangePicker";
import TransactionList from "./components/TransactionList";
import TransactionSummary from "./components/TransactionSummary";
import CategoryFilter from "./components/CategoryFilter";

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: 2,
      staleTime: 30000,
    },
  },
});

const App = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary>
        <DateRangeProvider>
          <TransactionProvider>
            <div className="min-h-screen bg-gray-100">
              <Header />
              <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
                <div className="relative z-10 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
                  <DateRangePicker />
                  <CategoryFilter />
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
            </div>
          </TransactionProvider>
        </DateRangeProvider>
      </ErrorBoundary>
    </QueryClientProvider>
  );
};

export default App;
