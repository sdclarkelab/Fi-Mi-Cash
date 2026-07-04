import React, { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getSyncStatus, triggerSync } from "../services/api";
import { useDateRange } from "../context/DateRangeContext";
import { useTransactionContext } from "../context/TransactionContext";

const formatRelative = (isoDate) => {
  if (!isoDate) return null;
  const then = new Date(isoDate);
  const minutes = Math.round((Date.now() - then.getTime()) / 60000);
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} hr ago`;
  return then.toLocaleDateString();
};

const SyncControl = () => {
  const [syncing, setSyncing] = useState(false);
  const [warning, setWarning] = useState(null);
  const queryClient = useQueryClient();
  const { appliedDateRange } = useDateRange();
  const { refetch } = useTransactionContext();

  const { data: status } = useQuery({
    queryKey: ["syncStatus"],
    queryFn: getSyncStatus,
  });

  const handleSync = async () => {
    setSyncing(true);
    setWarning(null);
    try {
      const result = await triggerSync({
        startDate: appliedDateRange.startDate,
        endDate: appliedDateRange.endDate,
      });
      if (result.failed > 0) {
        setWarning(
          `${result.failed} email(s) couldn't be parsed — they'll be retried automatically`
        );
      }
      queryClient.invalidateQueries({ queryKey: ["syncStatus"] });
      queryClient.invalidateQueries({ queryKey: ["transactionCount"] });
      await refetch();
    } catch (error) {
      setWarning(error.message);
    } finally {
      setSyncing(false);
    }
  };

  const lastSynced = formatRelative(status?.last_sync_date);

  return (
    <div className="flex items-center gap-3">
      {warning && <span className="text-sm text-amber-600">{warning}</span>}
      <span className="text-sm text-gray-500 whitespace-nowrap">
        {lastSynced ? `Last synced: ${lastSynced}` : "Never synced"}
      </span>
      <button
        onClick={handleSync}
        disabled={syncing}
        className="bg-white border border-gray-300 hover:bg-gray-50 text-gray-700 px-4 py-2 rounded-md text-sm font-medium focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 whitespace-nowrap"
      >
        {syncing ? "Syncing…" : "Sync now"}
      </button>
    </div>
  );
};

export default SyncControl;
