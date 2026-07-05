const HEADERS = [
  "date",
  "merchant",
  "amount",
  "original_currency",
  "original_amount",
  "exchange_rate",
  "primary_category",
  "subcategory",
  "confidence",
  "card_type",
  "source",
  "excluded",
  "description",
];

const escapeField = (value) => {
  if (value === null || value === undefined) return "";
  const str = String(value);
  if (/[",\n\r]/.test(str)) {
    return `"${str.replace(/"/g, '""')}"`;
  }
  return str;
};

export const buildTransactionsCsv = (transactions) => {
  const rows = transactions.map((tx) =>
    HEADERS.map((header) => escapeField(tx[header])).join(",")
  );
  return [HEADERS.join(","), ...rows].join("\r\n");
};
