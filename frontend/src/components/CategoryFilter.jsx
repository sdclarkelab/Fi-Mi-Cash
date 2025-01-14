// src/components/CategoryFilter.jsx
import React from "react";
import { useQuery } from "@tanstack/react-query";
import { fetchCategories } from "../services/api";
import { Menu } from "@headlessui/react";
import { HiChevronDown } from "react-icons/hi"; // Fixed icon import

const CategoryFilter = ({ onSelectCategory }) => {
  const { data: categories, isLoading } = useQuery({
    queryKey: ["categories"],
    queryFn: fetchCategories,
  });

  if (isLoading) return null;

  return (
    <div className="relative">
      <Menu>
        {({ open }) => (
          <>
            <Menu.Button className="inline-flex justify-center w-48 rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
              <span className="flex-1 text-left">Select Category</span>
              <HiChevronDown
                className="w-5 h-5 ml-2 -mr-1"
                aria-hidden="true"
              />
            </Menu.Button>

            <Menu.Items className="absolute right-0 mt-2 w-64 rounded-md shadow-lg bg-white ring-1 ring-black ring-opacity-5 focus:outline-none z-50">
              <div className="py-1 max-h-96 overflow-auto">
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
                            onClick={() => onSelectCategory(category)}
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
                                onSelectCategory(category, subcategory)
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
