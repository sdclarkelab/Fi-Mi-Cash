import { buildTransactionsCsv } from "./csv";

const HEADER =
  "date,merchant,amount,original_currency,original_amount,exchange_rate,primary_category,subcategory,confidence,card_type,source,excluded,description";

const tx = {
  date: "2026-06-15T12:30:00",
  merchant: "COFFEE SPOT",
  amount: 1500,
  original_currency: "JMD",
  original_amount: 1500,
  exchange_rate: null,
  primary_category: "Food & Dining",
  subcategory: "Coffee Shops",
  confidence: 0.9,
  card_type: "NCB VISA PLATINUM",
  source: "email",
  excluded: false,
  description: "test",
};

test("builds a header row plus one line per transaction", () => {
  const csv = buildTransactionsCsv([tx]);
  const lines = csv.split("\r\n");
  expect(lines).toHaveLength(2);
  expect(lines[0]).toBe(HEADER);
  expect(lines[1]).toContain("COFFEE SPOT");
  expect(lines[1]).toContain("1500");
});

test("escapes fields containing commas, quotes, and newlines", () => {
  const csv = buildTransactionsCsv([
    { ...tx, merchant: 'BURGER, THE "KING"', description: "line1\nline2" },
  ]);
  expect(csv).toContain('"BURGER, THE ""KING"""');
  expect(csv).toContain('"line1\nline2"');
});

test("renders null/undefined as empty; empty list is just the header", () => {
  expect(buildTransactionsCsv([])).toBe(HEADER);
  const csv = buildTransactionsCsv([
    { ...tx, exchange_rate: null, card_type: undefined },
  ]);
  const fields = csv.split("\r\n")[1].split(",");
  expect(fields[5]).toBe(""); // exchange_rate
  expect(fields[9]).toBe(""); // card_type
});
