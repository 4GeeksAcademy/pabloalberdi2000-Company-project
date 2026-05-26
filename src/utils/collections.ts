import { Employee, Restaurant, Sale, Supplier } from "../types/models";

export type SortDirection = "asc" | "desc";

export interface SalesFilterCriteria {
  restaurantId?: string;
  currency?: "COP" | "USD";
  minimumTotalAmount?: number;
  maximumTotalAmount?: number;
  fromDate?: string;
  toDate?: string;
}

export interface SupplierFilterCriteria {
  country?: "CO" | "US";
  category?: string;
  isActive?: boolean;
}

function isDateInRange(dateValue: string, fromDate?: string, toDate?: string): boolean {
  const dateTime = new Date(dateValue).getTime();

  if (Number.isNaN(dateTime)) {
    return false;
  }

  const fromTime = fromDate ? new Date(fromDate).getTime() : null;
  const toTime = toDate ? new Date(toDate).getTime() : null;

  const isAfterFrom = fromTime === null || (!Number.isNaN(fromTime) && dateTime >= fromTime);
  const isBeforeTo = toTime === null || (!Number.isNaN(toTime) && dateTime <= toTime);

  return isAfterFrom && isBeforeTo;
}

export function filterSalesByCriteria(sales: readonly Sale[], criteria: SalesFilterCriteria): Sale[] {
  return sales.filter((sale) => {
    const matchesRestaurant = !criteria.restaurantId || sale.restaurantId === criteria.restaurantId;
    const matchesCurrency = !criteria.currency || sale.total.currency === criteria.currency;
    const matchesMinimum =
      criteria.minimumTotalAmount === undefined || sale.total.amount >= criteria.minimumTotalAmount;
    const matchesMaximum =
      criteria.maximumTotalAmount === undefined || sale.total.amount <= criteria.maximumTotalAmount;
    const matchesDateRange = isDateInRange(sale.occurredAt, criteria.fromDate, criteria.toDate);

    return matchesRestaurant && matchesCurrency && matchesMinimum && matchesMaximum && matchesDateRange;
  });
}

export function filterSuppliersByCriteria(
  suppliers: readonly Supplier[],
  criteria: SupplierFilterCriteria,
): Supplier[] {
  return suppliers.filter((supplier) => {
    const matchesCountry = !criteria.country || supplier.country === criteria.country;
    const matchesCategory =
      !criteria.category || supplier.category.toLowerCase() === criteria.category.toLowerCase();
    const matchesStatus = criteria.isActive === undefined || supplier.isActive === criteria.isActive;

    return matchesCountry && matchesCategory && matchesStatus;
  });
}

export function sortSalesByTotalAmount(sales: readonly Sale[], direction: SortDirection = "asc"): Sale[] {
  const sortedSales = [...sales].sort((leftSale, rightSale) => leftSale.total.amount - rightSale.total.amount);
  return direction === "asc" ? sortedSales : sortedSales.reverse();
}

export function sortSuppliersByName(suppliers: readonly Supplier[], direction: SortDirection = "asc"): Supplier[] {
  const sortedSuppliers = [...suppliers].sort((leftSupplier, rightSupplier) =>
    leftSupplier.name.localeCompare(rightSupplier.name),
  );

  return direction === "asc" ? sortedSuppliers : sortedSuppliers.reverse();
}

export function sortRestaurantsByCountryAndCity(
  restaurants: readonly Restaurant[],
  direction: SortDirection = "asc",
): Restaurant[] {
  const sortedRestaurants = [...restaurants].sort((leftRestaurant, rightRestaurant) => {
    const countryComparison = leftRestaurant.country.localeCompare(rightRestaurant.country);
    if (countryComparison !== 0) {
      return countryComparison;
    }

    return leftRestaurant.city.localeCompare(rightRestaurant.city);
  });

  return direction === "asc" ? sortedRestaurants : sortedRestaurants.reverse();
}

export function sortEmployeesByHireDate(
  employees: readonly Employee[],
  direction: SortDirection = "asc",
): Employee[] {
  const sortedEmployees = [...employees].sort(
    (leftEmployee, rightEmployee) => new Date(leftEmployee.hireDate).getTime() - new Date(rightEmployee.hireDate).getTime(),
  );

  return direction === "asc" ? sortedEmployees : sortedEmployees.reverse();
}

export function groupSalesByRestaurantId(sales: readonly Sale[]): Record<string, Sale[]> {
  return sales.reduce<Record<string, Sale[]>>((groupedSales, sale) => {
    const existingSales = groupedSales[sale.restaurantId] ?? [];

    return {
      ...groupedSales,
      [sale.restaurantId]: [...existingSales, sale],
    };
  }, {});
}
