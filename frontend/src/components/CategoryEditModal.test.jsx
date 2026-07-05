import React from "react";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import CategoryEditModal from "./CategoryEditModal";

jest.mock("../services/api", () => ({
  addRule: jest.fn().mockResolvedValue({}),
  updateRule: jest.fn().mockResolvedValue({}),
  updateTransactionCategory: jest.fn().mockResolvedValue({}),
}));

const {
  addRule,
  updateTransactionCategory,
} = require("../services/api");

const transaction = {
  id: "tx-1",
  merchant: "COFFEE SPOT",
  primary_category: "Food & Dining",
  subcategory: "Coffee Shops",
};

const categories = {
  "Food & Dining": ["Coffee Shops"],
  Entertainment: ["Streaming"],
};

const renderModal = (onSuccess = jest.fn(), onClose = jest.fn()) => {
  render(
    <CategoryEditModal
      isOpen={true}
      onClose={onClose}
      transaction={transaction}
      categories={categories}
      onSuccess={onSuccess}
    />
  );
  return { onSuccess, onClose };
};

const pickEntertainmentStreaming = () => {
  fireEvent.change(screen.getByLabelText("Primary Category"), {
    target: { value: "Entertainment" },
  });
  fireEvent.change(screen.getByLabelText("Subcategory"), {
    target: { value: "Streaming" },
  });
};

describe("CategoryEditModal persistence", () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it("persists the edit for the single transaction when 'create rule' is unchecked", async () => {
    const { onSuccess } = renderModal();
    pickEntertainmentStreaming();

    fireEvent.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => {
      expect(updateTransactionCategory).toHaveBeenCalledWith(
        "tx-1",
        "Entertainment",
        "Streaming"
      );
    });
    expect(addRule).not.toHaveBeenCalled();
    expect(onSuccess).toHaveBeenCalled();
  });

  it("creates a merchant rule instead when 'create rule' is checked", async () => {
    const { onSuccess } = renderModal();
    pickEntertainmentStreaming();

    fireEvent.click(screen.getByLabelText(/create rule for all/i));
    fireEvent.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => {
      expect(addRule).toHaveBeenCalledWith(
        "COFFEE SPOT",
        "Entertainment",
        "Streaming"
      );
    });
    expect(onSuccess).toHaveBeenCalled();
  });

  it("surfaces an error and keeps the modal open when persistence fails", async () => {
    updateTransactionCategory.mockRejectedValueOnce(new Error("save failed"));
    const { onSuccess, onClose } = renderModal();
    pickEntertainmentStreaming();

    fireEvent.click(screen.getByRole("button", { name: /save changes/i }));

    await waitFor(() => {
      expect(screen.getByText("save failed")).toBeInTheDocument();
    });
    expect(onSuccess).not.toHaveBeenCalled();
    expect(onClose).not.toHaveBeenCalled();
  });
});
