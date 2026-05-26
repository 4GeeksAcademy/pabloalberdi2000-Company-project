import {
  AbsenceRecord,
  Customer,
  Employee,
  IngredientOrder,
  PurchaseRecord,
  Recipe,
  Restaurant,
  Sale,
  Supplier,
  ValidationResult,
} from "../types/models";

function createValidationResult(errors: string[]): ValidationResult {
  return {
    isValid: errors.length === 0,
    errors,
  };
}

function isValidDateString(dateValue: string): boolean {
  if (!dateValue.trim()) {
    return false;
  }

  const parsedDate = new Date(dateValue);
  return !Number.isNaN(parsedDate.getTime());
}

function validateRequiredText(fieldLabel: string, value: string): string[] {
  return value.trim().length === 0 ? [`${fieldLabel} is required.`] : [];
}

function validateEmailFormat(fieldLabel: string, email: string): string[] {
  const emailPattern = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  if (!email.trim()) {
    return [`${fieldLabel} is required.`];
  }

  return emailPattern.test(email) ? [] : [`${fieldLabel} must be a valid email address.`];
}

function validatePositiveNumber(fieldLabel: string, value: number, allowZero: boolean): string[] {
  if (!Number.isFinite(value)) {
    return [`${fieldLabel} must be a valid number.`];
  }

  if (allowZero) {
    return value < 0 ? [`${fieldLabel} cannot be negative.`] : [];
  }

  return value <= 0 ? [`${fieldLabel} must be greater than zero.`] : [];
}

export function validateRestaurant(restaurant: Restaurant): ValidationResult {
  const errors = [
    ...validateRequiredText("Restaurant id", restaurant.id),
    ...validateRequiredText("Restaurant name", restaurant.name),
    ...validateRequiredText("Restaurant city", restaurant.city),
    ...validateRequiredText("Restaurant address", restaurant.address),
    ...validateRequiredText("Restaurant timezone", restaurant.timezone),
  ];

  if (!isValidDateString(restaurant.openedAt)) {
    errors.push("Restaurant openedAt must be a valid date string.");
  }

  return createValidationResult(errors);
}

export function validateSupplier(supplier: Supplier): ValidationResult {
  const errors = [
    ...validateRequiredText("Supplier id", supplier.id),
    ...validateRequiredText("Supplier name", supplier.name),
    ...validateRequiredText("Supplier category", supplier.category),
    ...validateRequiredText("Supplier contactName", supplier.contactName),
    ...validateEmailFormat("Supplier email", supplier.email),
    ...validateRequiredText("Supplier phone", supplier.phone),
  ];

  return createValidationResult(errors);
}

export function validateCustomer(customer: Customer): ValidationResult {
  const errors = [
    ...validateRequiredText("Customer id", customer.id),
    ...validateRequiredText("Customer firstName", customer.firstName),
    ...validateRequiredText("Customer lastName", customer.lastName),
    ...validateEmailFormat("Customer email", customer.email),
    ...validateRequiredText("Customer phone", customer.phone),
    ...validateRequiredText("Customer preferredRestaurantId", customer.preferredRestaurantId),
  ];

  if (!isValidDateString(customer.createdAt)) {
    errors.push("Customer createdAt must be a valid date string.");
  }

  return createValidationResult(errors);
}

export function validateEmployee(employee: Employee): ValidationResult {
  const errors = [
    ...validateRequiredText("Employee id", employee.id),
    ...validateRequiredText("Employee firstName", employee.firstName),
    ...validateRequiredText("Employee lastName", employee.lastName),
    ...validateRequiredText("Employee restaurantId", employee.restaurantId),
    ...validateRequiredText("Employee role", employee.role),
  ];

  if (!isValidDateString(employee.hireDate)) {
    errors.push("Employee hireDate must be a valid date string.");
  }

  return createValidationResult(errors);
}

export function validateSale(sale: Sale): ValidationResult {
  const errors = [
    ...validateRequiredText("Sale id", sale.id),
    ...validateRequiredText("Sale restaurantId", sale.restaurantId),
    ...validateRequiredText("Sale ticketNumber", sale.ticketNumber),
    ...validatePositiveNumber("Sale covers", sale.covers, true),
    ...validatePositiveNumber("Sale subtotal amount", sale.subtotal.amount, true),
    ...validatePositiveNumber("Sale taxes amount", sale.taxes.amount, true),
    ...validatePositiveNumber("Sale total amount", sale.total.amount, true),
  ];

  if (!isValidDateString(sale.occurredAt)) {
    errors.push("Sale occurredAt must be a valid date string.");
  }

  const computedTotal = sale.subtotal.amount + sale.taxes.amount;
  if (Math.abs(computedTotal - sale.total.amount) > 0.0001) {
    errors.push("Sale total amount must equal subtotal plus taxes.");
  }

  return createValidationResult(errors);
}

export function validatePurchaseRecord(purchaseRecord: PurchaseRecord): ValidationResult {
  const errors = [
    ...validateRequiredText("PurchaseRecord id", purchaseRecord.id),
    ...validateRequiredText("PurchaseRecord supplierId", purchaseRecord.supplierId),
    ...validateRequiredText("PurchaseRecord restaurantId", purchaseRecord.restaurantId),
    ...validatePositiveNumber("PurchaseRecord totalAmount", purchaseRecord.totalAmount, false),
  ];

  if (!isValidDateString(purchaseRecord.purchasedAt)) {
    errors.push("PurchaseRecord purchasedAt must be a valid date string.");
  }

  return createValidationResult(errors);
}

export function validateIngredientOrder(ingredientOrder: IngredientOrder): ValidationResult {
  const errors = [
    ...validateRequiredText("IngredientOrder id", ingredientOrder.id),
    ...validateRequiredText("IngredientOrder supplierId", ingredientOrder.supplierId),
    ...validateRequiredText("IngredientOrder restaurantId", ingredientOrder.restaurantId),
  ];

  if (!isValidDateString(ingredientOrder.createdAt)) {
    errors.push("IngredientOrder createdAt must be a valid date string.");
  }

  if (!isValidDateString(ingredientOrder.expectedDeliveryAt)) {
    errors.push("IngredientOrder expectedDeliveryAt must be a valid date string.");
  }

  if (
    isValidDateString(ingredientOrder.createdAt) &&
    isValidDateString(ingredientOrder.expectedDeliveryAt) &&
    new Date(ingredientOrder.expectedDeliveryAt).getTime() < new Date(ingredientOrder.createdAt).getTime()
  ) {
    errors.push("IngredientOrder expectedDeliveryAt cannot be earlier than createdAt.");
  }

  if (ingredientOrder.lines.length === 0) {
    errors.push("IngredientOrder must include at least one line.");
  }

  const lineErrors = ingredientOrder.lines.flatMap((line, index) => [
    ...validateRequiredText(`IngredientOrder line ${index + 1} ingredientName`, line.ingredientName),
    ...validateRequiredText(`IngredientOrder line ${index + 1} unit`, line.unit),
    ...validatePositiveNumber(`IngredientOrder line ${index + 1} quantity`, line.quantity, false),
    ...validatePositiveNumber(`IngredientOrder line ${index + 1} unitPrice.amount`, line.unitPrice.amount, false),
  ]);

  return createValidationResult([...errors, ...lineErrors]);
}

export function validateAbsenceRecord(absenceRecord: AbsenceRecord): ValidationResult {
  const errors = [
    ...validateRequiredText("AbsenceRecord id", absenceRecord.id),
    ...validateRequiredText("AbsenceRecord employeeId", absenceRecord.employeeId),
    ...validateRequiredText("AbsenceRecord reason", absenceRecord.reason),
  ];

  if (!isValidDateString(absenceRecord.startDate)) {
    errors.push("AbsenceRecord startDate must be a valid date string.");
  }

  if (!isValidDateString(absenceRecord.endDate)) {
    errors.push("AbsenceRecord endDate must be a valid date string.");
  }

  if (
    isValidDateString(absenceRecord.startDate) &&
    isValidDateString(absenceRecord.endDate) &&
    new Date(absenceRecord.endDate).getTime() < new Date(absenceRecord.startDate).getTime()
  ) {
    errors.push("AbsenceRecord endDate cannot be earlier than startDate.");
  }

  return createValidationResult(errors);
}

export function validateRecipe(recipe: Recipe): ValidationResult {
  const errors = [
    ...validateRequiredText("Recipe id", recipe.id),
    ...validateRequiredText("Recipe code", recipe.code),
    ...validateRequiredText("Recipe name", recipe.name),
  ];

  if (recipe.version <= 0 || !Number.isInteger(recipe.version)) {
    errors.push("Recipe version must be a positive integer.");
  }

  if (recipe.ingredients.length === 0) {
    errors.push("Recipe must include at least one ingredient.");
  }

  if (recipe.steps.length === 0) {
    errors.push("Recipe must include at least one preparation step.");
  }

  if (!isValidDateString(recipe.updatedAt)) {
    errors.push("Recipe updatedAt must be a valid date string.");
  }

  return createValidationResult(errors);
}
