export type Id = string;

export type CountryCode = "CO" | "US";
export type CurrencyCode = "COP" | "USD";
export type LanguageCode = "es" | "en";

export type OrderChannel = "onsite" | "pickup" | "delivery" | "app";
export type ShiftName = "morning" | "afternoon" | "night";

export interface ValidationResult {
  isValid: boolean;
  errors: string[];
}

export interface MoneyAmount {
  amount: number;
  currency: CurrencyCode;
}

export interface Restaurant {
  id: Id;
  name: string;
  country: CountryCode;
  city: string;
  address: string;
  timezone: string;
  openedAt: string;
  isActive: boolean;
}

export interface Supplier {
  id: Id;
  name: string;
  country: CountryCode;
  category: string;
  contactName: string;
  email: string;
  phone: string;
  isActive: boolean;
}

export interface SupplierPriceRecord {
  id: Id;
  supplierId: Id;
  ingredientName: string;
  unit: string;
  unitPrice: MoneyAmount;
  effectiveFrom: string;
}

export interface MenuItem {
  id: Id;
  name: string;
  category: string;
  priceCop: number;
  priceUsd: number;
  isActive: boolean;
}

export interface Sale {
  id: Id;
  restaurantId: Id;
  occurredAt: string;
  channel: OrderChannel;
  ticketNumber: string;
  covers: number;
  subtotal: MoneyAmount;
  taxes: MoneyAmount;
  total: MoneyAmount;
}

export interface IngredientStock {
  id: Id;
  restaurantId: Id;
  ingredientName: string;
  unit: string;
  quantityOnHand: number;
  minThreshold: number;
  updatedAt: string;
}

export interface IngredientOrderLine {
  ingredientName: string;
  unit: string;
  quantity: number;
  unitPrice: MoneyAmount;
}

export interface IngredientOrder {
  id: Id;
  restaurantId: Id;
  supplierId: Id;
  createdAt: string;
  expectedDeliveryAt: string;
  status: "pending" | "approved" | "delivered" | "cancelled";
  lines: IngredientOrderLine[];
}

export interface PurchaseRecord {
  id: Id;
  supplierId: Id;
  restaurantId: Id;
  purchasedAt: string;
  currency: CurrencyCode;
  totalAmount: number;
}

export interface Customer {
  id: Id;
  firstName: string;
  lastName: string;
  email: string;
  phone: string;
  preferredLanguage: LanguageCode;
  preferredRestaurantId: Id;
  createdAt: string;
}

export interface LoyaltyAccount {
  customerId: Id;
  pointsBalance: number;
  tier: "base" | "silver" | "gold";
  updatedAt: string;
}

export interface LoyaltyMovement {
  id: Id;
  customerId: Id;
  saleId: Id;
  movementType: "earn" | "redeem" | "expire" | "adjust";
  points: number;
  createdAt: string;
}

export interface Employee {
  id: Id;
  firstName: string;
  lastName: string;
  country: CountryCode;
  restaurantId: Id;
  role: string;
  hireDate: string;
  isActive: boolean;
}

export interface ShiftReport {
  id: Id;
  restaurantId: Id;
  shiftDate: string;
  shiftName: ShiftName;
  managerEmployeeId: Id;
  coversServed: number;
  totalSales: MoneyAmount;
  incidents: string[];
}

export interface AbsenceRecord {
  id: Id;
  employeeId: Id;
  startDate: string;
  endDate: string;
  reason: string;
  status: "requested" | "approved" | "rejected";
}

export interface Recipe {
  id: Id;
  code: string;
  name: string;
  language: LanguageCode;
  version: number;
  ingredients: string[];
  steps: string[];
  updatedAt: string;
}

export interface RecipeUpdate {
  id: Id;
  recipeId: Id;
  version: number;
  changeSummary: string;
  publishedAt: string;
  targetRestaurantIds: Id[];
}

export interface TelemetryEvent {
  id: Id;
  restaurantId: Id;
  source: "pos" | "app" | "web" | "backoffice";
  eventType: "sale_created" | "order_placed" | "inventory_updated" | "heartbeat";
  occurredAt: string;
}

export const DEFAULT_VALIDATION_RESULT: ValidationResult = {
  isValid: true,
  errors: [],
};

export const EMPTY_MONEY_AMOUNT: MoneyAmount = {
  amount: 0,
  currency: "COP",
};

export const EMPTY_RESTAURANT: Restaurant = {
  id: "",
  name: "",
  country: "CO",
  city: "",
  address: "",
  timezone: "",
  openedAt: "",
  isActive: false,
};

export const EMPTY_SUPPLIER: Supplier = {
  id: "",
  name: "",
  country: "CO",
  category: "",
  contactName: "",
  email: "",
  phone: "",
  isActive: false,
};

export const EMPTY_CUSTOMER: Customer = {
  id: "",
  firstName: "",
  lastName: "",
  email: "",
  phone: "",
  preferredLanguage: "es",
  preferredRestaurantId: "",
  createdAt: "",
};

export const EMPTY_SALE: Sale = {
  id: "",
  restaurantId: "",
  occurredAt: "",
  channel: "onsite",
  ticketNumber: "",
  covers: 0,
  subtotal: { amount: 0, currency: "COP" },
  taxes: { amount: 0, currency: "COP" },
  total: { amount: 0, currency: "COP" },
};

export const EMPTY_EMPLOYEE: Employee = {
  id: "",
  firstName: "",
  lastName: "",
  country: "CO",
  restaurantId: "",
  role: "",
  hireDate: "",
  isActive: false,
};
