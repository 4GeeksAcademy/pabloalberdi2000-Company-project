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
  SupplierPriceRecord,
} from "../../types/models";

export const restaurantsFixture: Restaurant[] = [
  {
    id: "rest-1",
    name: "Brasaland Medellin Centro",
    country: "CO",
    city: "Medellin",
    address: "Cra 1 #10-20",
    timezone: "America/Bogota",
    openedAt: "2020-01-10",
    isActive: true,
  },
  {
    id: "rest-2",
    name: "Brasaland Miami Doral",
    country: "US",
    city: "Miami",
    address: "NW 36th St",
    timezone: "America/New_York",
    openedAt: "2021-06-01",
    isActive: true,
  },
  {
    id: "rest-3",
    name: "Brasaland Bogota Norte",
    country: "CO",
    city: "Bogota",
    address: "Calle 100",
    timezone: "America/Bogota",
    openedAt: "2022-03-15",
    isActive: false,
  },
];

export const suppliersFixture: Supplier[] = [
  {
    id: "sup-1",
    name: "Carnes Andinas",
    country: "CO",
    category: "meat",
    contactName: "Laura",
    email: "laura@andinas.co",
    phone: "+57-3000000001",
    isActive: true,
  },
  {
    id: "sup-2",
    name: "Florida Fresh",
    country: "US",
    category: "vegetables",
    contactName: "John",
    email: "john@flfresh.com",
    phone: "+1-3050000002",
    isActive: true,
  },
  {
    id: "sup-3",
    name: "Packing Pro",
    country: "CO",
    category: "packaging",
    contactName: "Maria",
    email: "maria@packingpro.co",
    phone: "+57-3000000003",
    isActive: false,
  },
];

export const salesFixture: Sale[] = [
  {
    id: "sale-1",
    restaurantId: "rest-1",
    occurredAt: "2026-05-20T10:00:00.000Z",
    channel: "onsite",
    ticketNumber: "A-100",
    covers: 4,
    subtotal: { amount: 100, currency: "COP" },
    taxes: { amount: 19, currency: "COP" },
    total: { amount: 119, currency: "COP" },
  },
  {
    id: "sale-2",
    restaurantId: "rest-1",
    occurredAt: "2026-05-21T10:00:00.000Z",
    channel: "delivery",
    ticketNumber: "A-101",
    covers: 2,
    subtotal: { amount: 200, currency: "COP" },
    taxes: { amount: 38, currency: "COP" },
    total: { amount: 238, currency: "COP" },
  },
  {
    id: "sale-3",
    restaurantId: "rest-2",
    occurredAt: "2026-05-22T10:00:00.000Z",
    channel: "app",
    ticketNumber: "M-100",
    covers: 3,
    subtotal: { amount: 30, currency: "USD" },
    taxes: { amount: 3, currency: "USD" },
    total: { amount: 33, currency: "USD" },
  },
];

export const sortedSalesByTotalFixture: Sale[] = [...salesFixture].sort(
  (leftSale, rightSale) => leftSale.total.amount - rightSale.total.amount,
);

export const supplierPriceHistoryFixture: SupplierPriceRecord[] = [
  {
    id: "pr-1",
    supplierId: "sup-1",
    ingredientName: "beef",
    unit: "kg",
    unitPrice: { amount: 20, currency: "USD" },
    effectiveFrom: "2026-04-01",
  },
  {
    id: "pr-2",
    supplierId: "sup-1",
    ingredientName: "chicken",
    unit: "kg",
    unitPrice: { amount: 12, currency: "USD" },
    effectiveFrom: "2026-04-01",
  },
  {
    id: "pr-3",
    supplierId: "sup-1",
    ingredientName: "potato",
    unit: "kg",
    unitPrice: { amount: 4, currency: "USD" },
    effectiveFrom: "2026-04-01",
  },
].sort((leftItem, rightItem) => leftItem.ingredientName.localeCompare(rightItem.ingredientName));

export const customersFixture: Customer[] = [
  {
    id: "cus-1",
    firstName: "Ana",
    lastName: "Gomez",
    email: "ana@correo.com",
    phone: "+57-3000000004",
    preferredLanguage: "es",
    preferredRestaurantId: "rest-1",
    createdAt: "2026-01-15",
  },
  {
    id: "cus-2",
    firstName: "Mike",
    lastName: "Ross",
    email: "mike@correo.com",
    phone: "+1-3050000005",
    preferredLanguage: "en",
    preferredRestaurantId: "rest-2",
    createdAt: "2026-02-01",
  },
];

export const employeesFixture: Employee[] = [
  {
    id: "emp-1",
    firstName: "Carlos",
    lastName: "Perez",
    country: "CO",
    restaurantId: "rest-1",
    role: "manager",
    hireDate: "2024-01-10",
    isActive: true,
  },
  {
    id: "emp-2",
    firstName: "Sofia",
    lastName: "Martinez",
    country: "US",
    restaurantId: "rest-2",
    role: "cook",
    hireDate: "2025-06-10",
    isActive: true,
  },
  {
    id: "emp-3",
    firstName: "Diego",
    lastName: "Lopez",
    country: "CO",
    restaurantId: "rest-3",
    role: "cashier",
    hireDate: "2023-03-01",
    isActive: false,
  },
];

export const purchaseRecordsFixture: PurchaseRecord[] = [
  {
    id: "pur-1",
    supplierId: "sup-1",
    restaurantId: "rest-1",
    purchasedAt: "2026-05-01",
    currency: "COP",
    totalAmount: 1000,
  },
  {
    id: "pur-2",
    supplierId: "sup-1",
    restaurantId: "rest-2",
    purchasedAt: "2026-05-03",
    currency: "USD",
    totalAmount: 500,
  },
  {
    id: "pur-3",
    supplierId: "sup-2",
    restaurantId: "rest-2",
    purchasedAt: "2026-05-04",
    currency: "USD",
    totalAmount: 750,
  },
];

export const validIngredientOrderFixture: IngredientOrder = {
  id: "ord-1",
  restaurantId: "rest-1",
  supplierId: "sup-1",
  createdAt: "2026-05-20",
  expectedDeliveryAt: "2026-05-22",
  status: "pending",
  lines: [
    {
      ingredientName: "beef",
      unit: "kg",
      quantity: 10,
      unitPrice: { amount: 20, currency: "USD" },
    },
  ],
};

export const validAbsenceRecordFixture: AbsenceRecord = {
  id: "abs-1",
  employeeId: "emp-1",
  startDate: "2026-06-01",
  endDate: "2026-06-05",
  reason: "vacation",
  status: "requested",
};

export const validRecipeFixture: Recipe = {
  id: "rec-1",
  code: "BRG-001",
  name: "Brasa Burger",
  language: "es",
  version: 1,
  ingredients: ["beef", "bun", "sauce"],
  steps: ["Grill beef", "Toast bun", "Assemble burger"],
  updatedAt: "2026-05-01",
};
