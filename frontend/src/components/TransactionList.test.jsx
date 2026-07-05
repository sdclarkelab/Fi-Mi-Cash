import React from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DateRangeProvider } from "../context/DateRangeContext";
import { TransactionProvider } from "../context/TransactionContext";
import TransactionList from "./TransactionList";

jest.mock("../services/api", () => ({
  fetchTransactions: jest.fn(),
  getTransactionCount: jest.fn(),
  toggleTransactionExclusion: jest.fn(),
  updateTransactionCategory: jest.fn(),
  deleteTransaction: jest.fn(),
}));

const apiModule = require("../services/api");
const { fetchTransactions, getTransactionCount } = apiModule;

const minimalTransaction = {
  id: 1,
  date: "2026-06-15T00:00:00",
  merchant: "Test Merchant",
  amount: 100,
  primary_category: "Food",
  subcategory: "Groceries",
  confidence: 0.9,
  card_type: "NCB VISA PLATINUM",
  source: "email",
  excluded: false,
};

const renderList = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <DateRangeProvider>
        <TransactionProvider>
          <TransactionList />
        </TransactionProvider>
      </DateRangeProvider>
    </QueryClientProvider>
  );
};

beforeEach(() => {
  jest.clearAllMocks();
  global.URL.createObjectURL = jest.fn(() => "blob:mock");
  global.URL.revokeObjectURL = jest.fn();
  fetchTransactions.mockResolvedValue({
    transactions: [minimalTransaction],
    transaction_summary: null,
    categories: {},
  });
  getTransactionCount.mockResolvedValue(1);
});

test("shows an error message when export fails", async () => {
  renderList();
  const button = await screen.findByRole("button", { name: /export csv/i });

  fetchTransactions.mockRejectedValueOnce(new Error("boom"));

  await userEvent.click(button);

  expect(await screen.findByText(/Export failed: boom/)).toBeInTheDocument();
});

test("shows a truncation notice when totalCount exceeds 1000", async () => {
  getTransactionCount.mockResolvedValue(1500);
  renderList();
  const button = await screen.findByRole("button", { name: /export csv/i });

  await userEvent.click(button);

  expect(
    await screen.findByText(/Exported first 1000 of 1500 transactions/)
  ).toBeInTheDocument();
});

test("shows no message on a full export", async () => {
  getTransactionCount.mockResolvedValue(1);
  renderList();
  const button = await screen.findByRole("button", { name: /export csv/i });

  await userEvent.click(button);

  await screen.findByRole("button", { name: /export csv/i, disabled: false });

  expect(screen.queryByText(/Export failed/)).not.toBeInTheDocument();
  expect(screen.queryByText(/Exported first/)).not.toBeInTheDocument();
});
