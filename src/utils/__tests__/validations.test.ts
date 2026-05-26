import { describe, expect, it } from "vitest";

import {
  validateAbsenceRecord,
  validateCustomer,
  validateEmployee,
  validateIngredientOrder,
  validatePurchaseRecord,
  validateRecipe,
  validateRestaurant,
  validateSale,
  validateSupplier,
} from "../validations";
import {
  customersFixture,
  employeesFixture,
  purchaseRecordsFixture,
  restaurantsFixture,
  salesFixture,
  suppliersFixture,
  validAbsenceRecordFixture,
  validIngredientOrderFixture,
  validRecipeFixture,
} from "./fixtures";

describe("validation utilities", () => {
  it("validates correct restaurant, supplier, customer and employee", () => {
    expect(validateRestaurant(restaurantsFixture[0]).isValid).toBe(true);
    expect(validateSupplier(suppliersFixture[0]).isValid).toBe(true);
    expect(validateCustomer(customersFixture[0]).isValid).toBe(true);
    expect(validateEmployee(employeesFixture[0]).isValid).toBe(true);
  });

  it("validates correct sale and purchase record", () => {
    expect(validateSale(salesFixture[0]).isValid).toBe(true);
    expect(validatePurchaseRecord(purchaseRecordsFixture[0]).isValid).toBe(true);
  });

  it("rejects sale with inconsistent total and invalid date", () => {
    const invalidSale = {
      ...salesFixture[0],
      occurredAt: "invalid-date",
      total: { ...salesFixture[0].total, amount: 999 },
    };

    const result = validateSale(invalidSale);
    expect(result.isValid).toBe(false);
    expect(result.errors.length).toBeGreaterThanOrEqual(2);
  });

  it("rejects invalid supplier email", () => {
    const invalidSupplier = {
      ...suppliersFixture[0],
      email: "bad-email",
    };

    const result = validateSupplier(invalidSupplier);
    expect(result.isValid).toBe(false);
    expect(result.errors.some((errorMessage) => errorMessage.includes("email"))).toBe(true);
  });

  it("rejects ingredient order with no lines and wrong date sequence", () => {
    const invalidOrder = {
      ...validIngredientOrderFixture,
      expectedDeliveryAt: "2026-05-19",
      lines: [],
    };

    const result = validateIngredientOrder(invalidOrder);
    expect(result.isValid).toBe(false);
    expect(result.errors.length).toBeGreaterThanOrEqual(2);
  });

  it("rejects absence record when end date is earlier than start date", () => {
    const invalidAbsence = {
      ...validAbsenceRecordFixture,
      startDate: "2026-06-10",
      endDate: "2026-06-05",
    };

    const result = validateAbsenceRecord(invalidAbsence);
    expect(result.isValid).toBe(false);
    expect(result.errors.some((errorMessage) => errorMessage.includes("earlier"))).toBe(true);
  });

  it("rejects recipe without ingredients and steps", () => {
    const invalidRecipe = {
      ...validRecipeFixture,
      ingredients: [],
      steps: [],
      version: 0,
    };

    const result = validateRecipe(invalidRecipe);
    expect(result.isValid).toBe(false);
    expect(result.errors.length).toBeGreaterThanOrEqual(3);
  });
});
