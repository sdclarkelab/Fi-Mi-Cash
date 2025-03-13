import React, { useState, useEffect } from "react";
import { addRule, updateRule } from "../services/api";

const CategoryEditModal = ({
  isOpen,
  onClose,
  transaction,
  categories,
  onSuccess,
}) => {
  const [primaryCategory, setPrimaryCategory] = useState("");
  const [subcategory, setSubcategory] = useState("");
  const [createRule, setCreateRule] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [availableSubcategories, setAvailableSubcategories] = useState([]);

  useEffect(() => {
    if (transaction) {
      setPrimaryCategory(transaction.primary_category || "");
      setSubcategory(transaction.subcategory || "");

      if (categories && primaryCategory) {
        setAvailableSubcategories(categories[primaryCategory] || []);
      }
    }
  }, [transaction, categories, isOpen]);

  useEffect(() => {
    if (categories && primaryCategory) {
      setAvailableSubcategories(categories[primaryCategory] || []);
      // Reset subcategory if current selection isn't available in the new primary category
      if (!categories[primaryCategory]?.includes(subcategory)) {
        setSubcategory("");
      }
    }
  }, [primaryCategory, categories]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setError(null);

    try {
      if (createRule) {
        // Create or update a merchant classification rule
        await addRule(transaction.merchant, primaryCategory, subcategory);
      }

      onSuccess(transaction.id, primaryCategory, subcategory, createRule);
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-gray-600 bg-opacity-75 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-medium text-gray-900">Edit Category</h3>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-500"
          >
            <span className="sr-only">Close</span>
            <svg
              className="h-6 w-6"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {error && (
          <div className="mb-4 bg-red-50 p-4 rounded-md">
            <div className="flex">
              <div className="text-sm text-red-700">{error}</div>
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Merchant
            </label>
            <div className="text-gray-900 font-medium">
              {transaction?.merchant}
            </div>
          </div>

          <div className="mb-4">
            <label
              htmlFor="category"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Primary Category
            </label>
            <select
              id="category"
              className="mt-1 block w-full pl-3 pr-10 py-2 text-base border border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
              value={primaryCategory}
              onChange={(e) => setPrimaryCategory(e.target.value)}
              required
            >
              <option value="">Select category</option>
              {categories &&
                Object.keys(categories).map((category) => (
                  <option key={category} value={category}>
                    {category}
                  </option>
                ))}
            </select>
          </div>

          <div className="mb-6">
            <label
              htmlFor="subcategory"
              className="block text-sm font-medium text-gray-700 mb-1"
            >
              Subcategory
            </label>
            <select
              id="subcategory"
              className="mt-1 block w-full pl-3 pr-10 py-2 text-base border border-gray-300 focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm rounded-md"
              value={subcategory}
              onChange={(e) => setSubcategory(e.target.value)}
              disabled={!primaryCategory}
            >
              <option value="">Select subcategory (optional)</option>
              {availableSubcategories.map((sub) => (
                <option key={sub} value={sub}>
                  {sub}
                </option>
              ))}
            </select>
          </div>

          <div className="mb-6">
            <div className="flex items-center">
              <input
                id="createRule"
                type="checkbox"
                className="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                checked={createRule}
                onChange={(e) => setCreateRule(e.target.checked)}
              />
              <label
                htmlFor="createRule"
                className="ml-2 block text-sm text-gray-900"
              >
                Create rule for all "{transaction?.merchant}" transactions
              </label>
            </div>
            <p className="mt-1 text-sm text-gray-500">
              This will categorize all transactions from this merchant
              automatically
            </p>
          </div>

          <div className="flex justify-end space-x-3">
            <button
              type="button"
              className="bg-white py-2 px-4 border border-gray-300 rounded-md shadow-sm text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              onClick={onClose}
              disabled={isSubmitting}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="inline-flex justify-center py-2 px-4 border border-transparent shadow-sm text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <span className="inline-flex items-center">
                  <svg
                    className="animate-spin -ml-1 mr-2 h-4 w-4 text-white"
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
                  Saving...
                </span>
              ) : (
                "Save Changes"
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default CategoryEditModal;
