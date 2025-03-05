import React, { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchCategories } from "../services/api";
import { Menu } from "@headlessui/react";
import { HiChevronDown } from "react-icons/hi";
import { useTransactionContext } from "../context/TransactionContext";

const CategoryFilter = () => {
  const { filters, updateFilters } = useTransactionContext();

  const { data: categories, isLoading } = useQuery({
    queryKey: [
      "categories",
      filters.startDate?.toISOString(),
      filters.endDate?.toISOString(),
    ],
    queryFn: () =>
      fetchCategories({
        startDate: filters.startDate,
        endDate: filters.endDate,
      }),
  });

  // Debug log to verify dates are being passed
  useEffect(() => {
    console.log("Category filter using dates:", {
      startDate: filters.startDate,
      endDate: filters.endDate,
    });
  }, [filters.startDate, filters.endDate]);

  const getDisplayText = () => {
    if (filters.category && filters.subcategory) {
      return `${filters.category} - ${filters.subcategory}`;
    }
    if (filters.category) {
      return filters.category;
    }
    return "All Categories";
  };

  const clearCategoryFilter = () => {
    updateFilters(null, null);
  };

  if (isLoading) return null;

  return (
    <div className="relative">
      <Menu>
        {({ open }) => (
          <>
            <Menu.Button className="inline-flex justify-center w-48 rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
              <span className="flex-1 text-left">{getDisplayText()}</span>
              <HiChevronDown
                className="w-5 h-5 ml-2 -mr-1"
                aria-hidden="true"
              />
            </Menu.Button>

            <Menu.Items className="absolute right-0 mt-2 w-64 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 focus:outline-none z-50">
              <div className="py-1 max-h-96 overflow-auto">
                <Menu.Item>
                  {({ active }) => (
                    <button
                      className={`${
                        active ? "bg-gray-100 text-gray-900" : "text-gray-700"
                      } w-full text-left px-4 py-2 text-sm font-medium border-l-4 ${
                        active ? "border-blue-500" : "border-transparent"
                      }`}
                      onClick={clearCategoryFilter}
                    >
                      All Categories
                    </button>
                  )}
                </Menu.Item>

                {Object.entries(categories || {}).map(
                  ([category, subcategories]) => (
                    <div key={category} className="category-group">
                      <Menu.Item>
                        {({ active }) => (
                          <button
                            className={`${
                              active
                                ? "bg-gray-100 text-gray-900"
                                : "text-gray-700"
                            } w-full text-left px-4 py-2 text-sm font-medium border-l-4 ${
                              active ? "border-blue-500" : "border-transparent"
                            }`}
                            onClick={() => updateFilters(category)}
                          >
                            {category}
                          </button>
                        )}
                      </Menu.Item>

                      {subcategories.map((subcategory) => (
                        <Menu.Item key={`${category}-${subcategory}`}>
                          {({ active }) => (
                            <button
                              className={`${
                                active
                                  ? "bg-gray-100 text-gray-900"
                                  : "text-gray-600"
                              } w-full text-left px-8 py-2 text-sm border-l-4 ${
                                active
                                  ? "border-blue-300"
                                  : "border-transparent"
                              }`}
                              onClick={() =>
                                updateFilters(category, subcategory)
                              }
                            >
                              {subcategory}
                            </button>
                          )}
                        </Menu.Item>
                      ))}
                    </div>
                  )
                )}
              </div>
            </Menu.Items>
          </>
        )}
      </Menu>
    </div>
  );
};

export default CategoryFilter;
