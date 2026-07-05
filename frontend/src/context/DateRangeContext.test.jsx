import React from "react";
import { render, act } from "@testing-library/react";
import { DateRangeProvider, useDateRange } from "./DateRangeContext";

let ctx;
const GrabContext = () => {
  ctx = useDateRange();
  return null;
};

const renderProvider = () =>
  render(
    <DateRangeProvider>
      <GrabContext />
    </DateRangeProvider>
  );

const expectEndOfDay = (date, year, month, day) => {
  expect(date.getFullYear()).toBe(year);
  expect(date.getMonth()).toBe(month);
  expect(date.getDate()).toBe(day);
  expect(date.getHours()).toBe(23);
  expect(date.getMinutes()).toBe(59);
  expect(date.getSeconds()).toBe(59);
};

describe("DateRangeContext end-of-day handling", () => {
  it("applies the end date as end-of-day so the whole end day is included", () => {
    renderProvider();
    act(() => {
      ctx.setAppliedDateRange({
        startDate: new Date(2026, 5, 1, 10, 15),
        endDate: new Date(2026, 5, 20, 14, 30),
      });
    });

    expectEndOfDay(ctx.appliedDateRange.endDate, 2026, 5, 20);

    // Start date still floors to start-of-day
    const start = ctx.appliedDateRange.startDate;
    expect(start.getDate()).toBe(1);
    expect(start.getHours()).toBe(0);
    expect(start.getMinutes()).toBe(0);
  });

  it("stores the draft end date as end-of-day too", () => {
    renderProvider();
    act(() => {
      ctx.setDateRange({
        startDate: new Date(2026, 5, 1),
        endDate: new Date(2026, 5, 20, 9, 0),
      });
    });

    expectEndOfDay(ctx.dateRange.endDate, 2026, 5, 20);
  });

  it("initializes the end date at end of today", () => {
    renderProvider();
    const today = new Date();
    expectEndOfDay(
      ctx.appliedDateRange.endDate,
      today.getFullYear(),
      today.getMonth(),
      today.getDate()
    );
    expectEndOfDay(
      ctx.dateRange.endDate,
      today.getFullYear(),
      today.getMonth(),
      today.getDate()
    );
  });
});
