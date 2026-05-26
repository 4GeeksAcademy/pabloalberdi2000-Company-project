import { describe, expect, it } from "vitest";

import {
  calculateAverageTicketByRestaurant,
  calculateSalesTotalsByCurrency,
  countEmployeesByCountry,
  countSalesByRestaurant,
  findHighestTicketSale,
  findLowestTicketSale,
  findRestaurantWithHighestAverageTicket,
  findRestaurantWithLowestAverageTicket,
  summarizePurchasesBySupplier,
} from "../transformations";
import { employeesFixture, purchaseRecordsFixture, salesFixture } from "./fixtures";

describe("transformation utilities", () => {
  it("counts sales by restaurant", () => {
    const counts = countSalesByRestaurant(salesFixture);
    expect(counts).toEqual({
      "rest-1": 2,
      "rest-2": 1,
    });
  });

  it("calculates sales totals by currency", () => {
    const totals = calculateSalesTotalsByCurrency(salesFixture);
    expect(totals).toEqual({
      COP: 357,
      USD: 33,
    });
  });

  it("calculates average ticket by restaurant", () => {
    const averages = calculateAverageTicketByRestaurant(salesFixture);
    expect(averages).toEqual({
      "rest-1": 178.5,
      "rest-2": 33,
    });
  });

  it("returns highest and lowest ticket sale", () => {
    const highestSale = findHighestTicketSale(salesFixture);
    const lowestSale = findLowestTicketSale(salesFixture);

    expect(highestSale?.id).toBe("sale-2");
    expect(lowestSale?.id).toBe("sale-3");
  });

  it("returns undefined for max and min on empty sales", () => {
    expect(findHighestTicketSale([])).toBeUndefined();
    expect(findLowestTicketSale([])).toBeUndefined();
  });

  it("summarizes purchases by supplier", () => {
    const summary = summarizePurchasesBySupplier(purchaseRecordsFixture);
    expect(summary).toEqual({
      "sup-1": 1500,
      "sup-2": 750,
    });
  });

  it("counts employees by country", () => {
    const counts = countEmployeesByCountry(employeesFixture);
    expect(counts).toEqual({
      CO: 2,
      US: 1,
    });
  });

  it("finds restaurants with highest and lowest average ticket", () => {
    const highestAverage = findRestaurantWithHighestAverageTicket(salesFixture);
    const lowestAverage = findRestaurantWithLowestAverageTicket(salesFixture);

    expect(highestAverage).toEqual({
      restaurantId: "rest-1",
      averageTicket: 178.5,
    });
    expect(lowestAverage).toEqual({
      restaurantId: "rest-2",
      averageTicket: 33,
    });
  });
});
