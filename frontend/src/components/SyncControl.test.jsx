import React from "react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { DateRangeProvider } from "../context/DateRangeContext";
import { TransactionProvider } from "../context/TransactionContext";
import SyncControl from "./SyncControl";

jest.mock("../services/api", () => ({
  fetchTransactions: jest.fn(),
  getTransactionCount: jest.fn(),
  getSyncStatus: jest.fn(),
  triggerSync: jest.fn(),
}));

const {
  fetchTransactions,
  getTransactionCount,
  getSyncStatus,
  triggerSync,
} = require("../services/api");

const renderControl = () => {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <DateRangeProvider>
        <TransactionProvider>
          <SyncControl />
        </TransactionProvider>
      </DateRangeProvider>
    </QueryClientProvider>
  );
};

beforeEach(() => {
  jest.clearAllMocks();
  const now = new Date().toISOString();
  fetchTransactions.mockResolvedValue({
    transactions: [],
    transaction_summary: null,
    categories: {},
  });
  getTransactionCount.mockResolvedValue(0);
  getSyncStatus.mockResolvedValue({
    last_sync_date: now,
    synced_start_date: "2026-06-01T00:00:00",
    synced_end_date: "2026-06-30T23:59:59",
  });
  triggerSync.mockResolvedValue({
    fetched: 2,
    stored: 1,
    skipped: 1,
    failed: 0,
    last_sync_date: now,
  });
});

test("shows last-synced time and a Sync now button", async () => {
  renderControl();
  expect(await screen.findByText(/Last synced:/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /sync now/i })).toBeInTheDocument();
});

test("triggers a sync for the applied date range on click", async () => {
  renderControl();
  await userEvent.click(screen.getByRole("button", { name: /sync now/i }));
  await waitFor(() => expect(triggerSync).toHaveBeenCalledTimes(1));
  const arg = triggerSync.mock.calls[0][0];
  expect(arg.startDate).toBeInstanceOf(Date);
  expect(arg.endDate).toBeInstanceOf(Date);
});

test("shows a warning when some emails failed to parse", async () => {
  triggerSync.mockResolvedValueOnce({
    fetched: 3,
    stored: 1,
    skipped: 0,
    failed: 2,
    last_sync_date: new Date().toISOString(),
  });
  renderControl();
  await userEvent.click(screen.getByRole("button", { name: /sync now/i }));
  expect(
    await screen.findByText(/2 email\(s\) couldn't be parsed/)
  ).toBeInTheDocument();
});
