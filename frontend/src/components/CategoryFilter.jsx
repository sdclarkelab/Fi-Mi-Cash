import React, { useState, useRef, useEffect } from "react";
import { Menu } from "@headlessui/react";
import { HiChevronDown, HiCheck, HiX } from "react-icons/hi";
import { useTransactionContext } from "../context/TransactionContext";

const CategoryFilter = () => {
  const { filters, updateFilters, transactionData, isLoading } =
    useTransactionContext();
  
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef(null);

  // Handle clicking outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const getDisplayText = () => {
    if (!filters.categories || filters.categories.length === 0) {
      return "All Categories";
    }
    if (filters.categories.length === 1) {
      const selected = filters.categories[0];
      return selected.subcategory ? `${selected.category} - ${selected.subcategory}` : selected.category;
    }
    return `${filters.categories.length} categories selected`;
  };

  const clearCategoryFilter = () => {
    updateFilters([]);
  };

  const isSelected = (category, subcategory = null) => {
    if (!filters.categories) return false;
    return filters.categories.some(item => 
      item.category === category && item.subcategory === subcategory
    );
  };

  const toggleCategory = (category, subcategory = null) => {
    const currentSelections = filters.categories || [];
    const isCurrentlySelected = isSelected(category, subcategory);

    let newSelections;
    if (isCurrentlySelected) {
      // Remove the selection
      newSelections = currentSelections.filter(item => 
        !(item.category === category && item.subcategory === subcategory)
      );
    } else {
      // Add the selection
      newSelections = [...currentSelections, { category, subcategory }];
    }

    updateFilters(newSelections);
  };

  const removeSelection = (category, subcategory = null) => {
    const newSelections = (filters.categories || []).filter(item => 
      !(item.category === category && item.subcategory === subcategory)
    );
    updateFilters(newSelections);
  };

  if (isLoading) return null;

  // Extract categories from transaction data
  const categories = transactionData?.categories || {};
  const selectedCategories = filters.categories || [];

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Main dropdown button */}
      <button
        className="inline-flex justify-center w-48 rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        onClick={() => setIsOpen(!isOpen)}
      >
        <span className="flex-1 text-left truncate">{getDisplayText()}</span>
        <HiChevronDown
          className={`w-5 h-5 ml-2 -mr-1 transition-transform ${isOpen ? 'rotate-180' : ''}`}
          aria-hidden="true"
        />
      </button>

      {/* Selected categories pills */}
      {selectedCategories.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {selectedCategories.map((selection, index) => (
            <span
              key={`${selection.category}-${selection.subcategory || 'main'}`}
              className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
            >
              {selection.subcategory ? `${selection.category} - ${selection.subcategory}` : selection.category}
              <button
                type="button"
                className="ml-1 inline-flex items-center justify-center w-4 h-4 rounded-full text-blue-600 hover:bg-blue-200 hover:text-blue-900"
                onClick={() => removeSelection(selection.category, selection.subcategory)}
              >
                <HiX className="w-3 h-3" />
              </button>
            </span>
          ))}
          {selectedCategories.length > 0 && (
            <button
              type="button"
              className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-700 hover:bg-gray-200"
              onClick={clearCategoryFilter}
            >
              Clear all
              <HiX className="w-3 h-3 ml-1" />
            </button>
          )}
        </div>
      )}

      {/* Dropdown menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-72 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 focus:outline-none z-50">
          <div className="py-1 max-h-96 overflow-auto">
            {/* All Categories Option */}
            <button
              className={`w-full text-left px-4 py-3 text-sm font-medium flex items-center justify-between group hover:bg-gray-50 ${
                selectedCategories.length === 0 ? "bg-blue-50 border-l-4 border-blue-500 text-blue-900" : "text-gray-700"
              }`}
              onClick={clearCategoryFilter}
            >
              <span className="flex items-center">
                <span className="w-2 h-2 bg-gray-400 rounded-full mr-3"></span>
                All Categories
              </span>
              {selectedCategories.length === 0 && (
                <HiCheck className="w-4 h-4 text-blue-600" />
              )}
            </button>

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

                {/* Primary Category Checkbox */}
                <button
                  className={`w-full text-left px-4 py-2.5 text-sm font-medium flex items-center justify-between group hover:bg-blue-50 ${
                    isSelected(category) 
                      ? "bg-blue-50 border-l-4 border-blue-500 text-blue-900" 
                      : "text-gray-700 hover:text-blue-900"
                  }`}
                  onClick={() => toggleCategory(category)}
                >
                  <span className="flex items-center">
                    <span className={`w-3 h-3 rounded-sm mr-3 flex-shrink-0 ${
                      isSelected(category) ? 'bg-blue-500' : 'bg-gray-300'
                    }`}></span>
                    <span className="font-medium">{category}</span>
                  </span>
                  {isSelected(category) && (
                    <HiCheck className="w-4 h-4 text-blue-600" />
                  )}
                </button>

                {/* Subcategories with checkboxes */}
                <div className="bg-white">
                  {subcategories.map((subcategory) => (
                    <button
                      key={`${category}-${subcategory}`}
                      className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-50 hover:text-gray-900 flex items-center justify-between group ${
                        isSelected(category, subcategory)
                          ? "bg-blue-50 border-l-4 border-blue-300 text-blue-900"
                          : "border-l-4 border-transparent text-gray-600"
                      }`}
                      onClick={() => toggleCategory(category, subcategory)}
                    >
                      <span className="flex items-center">
                        <span className="w-6 flex justify-center mr-2">
                          <span className={`w-1.5 h-1.5 rounded-full ${
                            isSelected(category, subcategory) ? 'bg-blue-500' : 'bg-gray-400'
                          }`}></span>
                        </span>
                        <span>{subcategory}</span>
                      </span>
                      {isSelected(category, subcategory) && (
                        <HiCheck className="w-4 h-4 text-blue-600" />
                      )}
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};

export default CategoryFilter;
