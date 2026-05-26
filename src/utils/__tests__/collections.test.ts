import { describe, expect, it } from "vitest";

import {
  filterSalesByCriteria,
  filterSuppliersByCriteria,
  groupSalesByRestaurantId,
  sortRestaurantsByCountryAndCity,
  sortSalesByTotalAmount,
  sortSuppliersByName,
} from "../collections";
import { restaurantsFixture, salesFixture, suppliersFixture } from "./fixtures";

describe("collections utilities", () => {
  it("filters sales with combined criteria", () => {
    const filteredSales = filterSalesByCriteria(salesFixture, {
      restaurantId: "rest-1",
      minimumTotalAmount: 120,
      fromDate: "2026-05-20T00:00:00.000Z",
      toDate: "2026-05-22T00:00:00.000Z",
    });

    expect(filteredSales).toHaveLength(1);
    expect(filteredSales[0].id).toBe("sale-2");
  });

  it("returns empty array when filtering empty sales", () => {
    const filteredSales = filterSalesByCriteria([], { restaurantId: "rest-1" });
    expect(filteredSales).toEqual([]);
  });

  it("filters suppliers by country, category and status", () => {
    const filteredSuppliers = filterSuppliersByCriteria(suppliersFixture, {
      country: "CO",
      category: "MEAT",
      isActive: true,
    });

    expect(filteredSuppliers).toHaveLength(1);
    expect(filteredSuppliers[0].id).toBe("sup-1");
  });

  it("sorts sales by total amount in both directions without mutating input", () => {
    const originalIds = salesFixture.map((sale) => sale.id);

    const ascending = sortSalesByTotalAmount(salesFixture, "asc");
    const descending = sortSalesByTotalAmount(salesFixture, "desc");

    expect(ascending.map((sale) => sale.id)).toEqual(["sale-3", "sale-1", "sale-2"]);
    expect(descending.map((sale) => sale.id)).toEqual(["sale-2", "sale-1", "sale-3"]);
    expect(salesFixture.map((sale) => sale.id)).toEqual(originalIds);
  });

  it("sorts suppliers by name", () => {
    const sortedSuppliers = sortSuppliersByName(suppliersFixture, "asc");
    expect(sortedSuppliers.map((supplier) => supplier.name)).toEqual([
      "Carnes Andinas",
      "Florida Fresh",
      "Packing Pro",
    ]);
  });

  it("sorts restaurants by country and city", () => {
    const sortedRestaurants = sortRestaurantsByCountryAndCity(restaurantsFixture, "asc");
    expect(sortedRestaurants.map((restaurant) => `${restaurant.country}-${restaurant.city}`)).toEqual([
      "CO-Bogota",
      "CO-Medellin",
      "US-Miami",
    ]);
  });

  it("groups sales by restaurant id", () => {
    const groupedSales = groupSalesByRestaurantId(salesFixture);
    expect(Object.keys(groupedSales).sort()).toEqual(["rest-1", "rest-2"]);
    expect(groupedSales["rest-1"]).toHaveLength(2);
    expect(groupedSales["rest-2"]).toHaveLength(1);
  });
});
