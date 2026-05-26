import { describe, expect, it } from "vitest";

import {
  binarySearchSaleByTotalAmount,
  binarySearchSupplierPriceByIngredientName,
  findCustomerByEmail,
  findRestaurantById,
  findSupplierByName,
} from "../search";
import {
  customersFixture,
  restaurantsFixture,
  sortedSalesByTotalFixture,
  supplierPriceHistoryFixture,
  suppliersFixture,
} from "./fixtures";

describe("search utilities", () => {
  it("finds a restaurant by id using linear search", () => {
    const restaurant = findRestaurantById(restaurantsFixture, "rest-2");
    expect(restaurant?.name).toBe("Brasaland Miami Doral");
  });

  it("returns undefined when restaurant id is not found", () => {
    const restaurant = findRestaurantById(restaurantsFixture, "rest-999");
    expect(restaurant).toBeUndefined();
  });

  it("finds a supplier by name in case-insensitive way", () => {
    const supplier = findSupplierByName(suppliersFixture, "florida fresh");
    expect(supplier?.id).toBe("sup-2");
  });

  it("finds customer by email in case-insensitive way", () => {
    const customer = findCustomerByEmail(customersFixture, "ANA@CORREO.COM");
    expect(customer?.id).toBe("cus-1");
  });

  it("finds sale by total amount with binary search", () => {
    const sale = binarySearchSaleByTotalAmount(sortedSalesByTotalFixture, 119);
    expect(sale?.id).toBe("sale-1");
  });

  it("returns undefined for binary search on empty sales array", () => {
    const sale = binarySearchSaleByTotalAmount([], 100);
    expect(sale).toBeUndefined();
  });

  it("finds supplier price record by ingredient name with binary search", () => {
    const priceRecord = binarySearchSupplierPriceByIngredientName(supplierPriceHistoryFixture, "CHICKEN");
    expect(priceRecord?.id).toBe("pr-2");
  });

  it("returns undefined when ingredient name is not found", () => {
    const priceRecord = binarySearchSupplierPriceByIngredientName(supplierPriceHistoryFixture, "onion");
    expect(priceRecord).toBeUndefined();
  });
});
