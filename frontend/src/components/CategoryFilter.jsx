import React from "react";
import { Menu } from "@headlessui/react";
import { HiChevronDown, HiCheck } from "react-icons/hi";
import { useTransactionContext } from "../context/TransactionContext";

const CategoryFilter = () => {
  const { filters, updateFilters, transactionData, isLoading } =
    useTransactionContext();

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

  // Extract categories from transaction data
  const categories = transactionData?.categories || {};

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

            <Menu.Items className="absolute right-0 mt-2 w-72 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 focus:outline-none z-50">
              <div className="py-1 max-h-96 overflow-auto">
                {/* All Categories Option */}
                <Menu.Item>
                  {({ active }) => (
                    <button
                      className={`${
                        active ? "bg-blue-50 text-blue-900" : "text-gray-700"
                      } w-full text-left px-4 py-3 text-sm font-medium flex items-center justify-between group ${
                        !filters.category ? "bg-blue-50 border-l-4 border-blue-500 text-blue-900" : ""
                      }`}
                      onClick={clearCategoryFilter}
                    >
                      <span className="flex items-center">
                        <span className="w-2 h-2 bg-gray-400 rounded-full mr-3"></span>
                        All Categories
                      </span>
                      {!filters.category && (
                        <HiCheck className="w-4 h-4 text-blue-600" />
                      )}
                    </button>
                  )}
                </Menu.Item>

                {/* Category Groups */}
                {Object.entries(categories).map(([category, subcategories]) => (
                  <div key={category} className="category-group border-b border-gray-100 last:border-b-0">
                    {/* Category Group Header */}
                    <div className="bg-gray-50 px-3 py-2 border-b border-gray-200">
                      <div className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
                        {category}
                        <span className="text-gray-400 font-normal ml-2">
                          ({subcategories.length + 1} options)
                        </span>
                      </div>
                    </div>

                    {/* Primary Category Button */}
                    <Menu.Item>
                      {({ active }) => (
                        <button
                          className={`${
                            active ? "bg-blue-50 text-blue-900" : "text-gray-700"
                          } w-full text-left px-4 py-2.5 text-sm font-medium flex items-center justify-between group ${
                            filters.category === category && !filters.subcategory 
                              ? "bg-blue-50 border-l-4 border-blue-500 text-blue-900" 
                              : ""
                          }`}
                          onClick={() => updateFilters(category)}
                        >
                          <span className="flex items-center">
                            <span className="w-3 h-3 bg-blue-500 rounded-sm mr-3 flex-shrink-0"></span>
                            <span className="font-medium">{category}</span>
                          </span>
                          {filters.category === category && !filters.subcategory && (
                            <HiCheck className="w-4 h-4 text-blue-600" />
                          )}
                        </button>
                      )}
                    </Menu.Item>

                    {/* Subcategories with better visual distinction */}
                    <div className="bg-white">
                      {subcategories.map((subcategory) => (
                        <Menu.Item key={`${category}-${subcategory}`}>
                          {({ active }) => (
                            <button
                              className={`${
                                active ? "bg-gray-50 text-gray-900" : "text-gray-600"
                              } w-full text-left px-4 py-2 text-sm hover:bg-gray-50 hover:text-gray-900 flex items-center justify-between group ${
                                filters.category === category && filters.subcategory === subcategory
                                  ? "bg-blue-50 border-l-4 border-blue-300 text-blue-900"
                                  : "border-l-4 border-transparent"
                              }`}
                              onClick={() => updateFilters(category, subcategory)}
                            >
                              <span className="flex items-center">
                                <span className="w-6 flex justify-center mr-2">
                                  <span className="w-1.5 h-1.5 bg-gray-400 rounded-full"></span>
                                </span>
                                <span>{subcategory}</span>
                              </span>
                              {filters.category === category && filters.subcategory === subcategory && (
                                <HiCheck className="w-4 h-4 text-blue-600" />
                              )}
                            </button>
                          )}
                        </Menu.Item>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </Menu.Items>
          </>
        )}
      </Menu>
    </div>
  );
};

export default CategoryFilter;
