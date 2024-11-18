import React, { useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DateRangeProvider } from "./context/DateRangeContext";
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
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [selectedSubcategory, setSelectedSubcategory] = useState(null);

  const handleCategorySelect = (category, subcategory = null) => {
    setSelectedCategory(category);
    setSelectedSubcategory(subcategory);
  };

  return (
    <QueryClientProvider client={queryClient}>
      <ErrorBoundary>
        <DateRangeProvider>
          <div className="min-h-screen bg-gray-100">
            <Header />
            <main className="max-w-7xl mx-auto py-6 px-4 sm:px-6 lg:px-8">
              {/* Added relative positioning and z-index to the filters container */}
              <div className="relative z-10 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
                <DateRangePicker />
                <CategoryFilter onSelectCategory={handleCategorySelect} />
              </div>

              {/* Removed z-index from content area */}
              <div className="space-y-6">
                <ErrorBoundary>
                  <TransactionSummary />
                </ErrorBoundary>
                <ErrorBoundary>
                  <TransactionList
                    category={selectedCategory}
                    subcategory={selectedSubcategory}
                  />
                </ErrorBoundary>
              </div>
            </main>
          </div>
        </DateRangeProvider>
      </ErrorBoundary>
    </QueryClientProvider>
  );
};

export default App;
