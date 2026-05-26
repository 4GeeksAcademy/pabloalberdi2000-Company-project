import { CurrencyCode, Employee, PurchaseRecord, Sale } from "../types/models";

interface RestaurantAverageTicket {
  restaurantId: string;
  averageTicket: number;
}

function calculateAverage(values: readonly number[]): number | null {
  if (values.length === 0) {
    return null;
  }

  const total = values.reduce((runningTotal, value) => runningTotal + value, 0);
  return total / values.length;
}

export function countSalesByRestaurant(sales: readonly Sale[]): Record<string, number> {
  return sales.reduce<Record<string, number>>((countByRestaurant, sale) => {
    const previousCount = countByRestaurant[sale.restaurantId] ?? 0;
    return {
      ...countByRestaurant,
      [sale.restaurantId]: previousCount + 1,
    };
  }, {});
}

export function calculateSalesTotalsByCurrency(sales: readonly Sale[]): Record<CurrencyCode, number> {
  return sales.reduce<Record<CurrencyCode, number>>(
    (totalByCurrency, sale) => ({
      ...totalByCurrency,
      [sale.total.currency]: totalByCurrency[sale.total.currency] + sale.total.amount,
    }),
    { COP: 0, USD: 0 },
  );
}

export function calculateAverageTicketByRestaurant(sales: readonly Sale[]): Record<string, number | null> {
  const saleAmountsByRestaurant = sales.reduce<Record<string, number[]>>((amountsByRestaurant, sale) => {
    const currentAmounts = amountsByRestaurant[sale.restaurantId] ?? [];

    return {
      ...amountsByRestaurant,
      [sale.restaurantId]: [...currentAmounts, sale.total.amount],
    };
  }, {});

  return Object.entries(saleAmountsByRestaurant).reduce<Record<string, number | null>>(
    (averageByRestaurant, [restaurantId, amounts]) => ({
      ...averageByRestaurant,
      [restaurantId]: calculateAverage(amounts),
    }),
    {},
  );
}

export function findHighestTicketSale(sales: readonly Sale[]): Sale | undefined {
  return sales.reduce<Sale | undefined>((highestSale, sale) => {
    if (!highestSale) {
      return sale;
    }

    return sale.total.amount > highestSale.total.amount ? sale : highestSale;
  }, undefined);
}

export function findLowestTicketSale(sales: readonly Sale[]): Sale | undefined {
  return sales.reduce<Sale | undefined>((lowestSale, sale) => {
    if (!lowestSale) {
      return sale;
    }

    return sale.total.amount < lowestSale.total.amount ? sale : lowestSale;
  }, undefined);
}

export function summarizePurchasesBySupplier(purchases: readonly PurchaseRecord[]): Record<string, number> {
  return purchases.reduce<Record<string, number>>((totalBySupplier, purchase) => {
    const previousTotal = totalBySupplier[purchase.supplierId] ?? 0;
    return {
      ...totalBySupplier,
      [purchase.supplierId]: previousTotal + purchase.totalAmount,
    };
  }, {});
}

export function countEmployeesByCountry(employees: readonly Employee[]): Record<string, number> {
  return employees.reduce<Record<string, number>>((countByCountry, employee) => {
    const previousCount = countByCountry[employee.country] ?? 0;

    return {
      ...countByCountry,
      [employee.country]: previousCount + 1,
    };
  }, {});
}

export function findRestaurantWithHighestAverageTicket(sales: readonly Sale[]): RestaurantAverageTicket | undefined {
  const averagesByRestaurant = calculateAverageTicketByRestaurant(sales);

  return Object.entries(averagesByRestaurant).reduce<RestaurantAverageTicket | undefined>(
    (highestAverage, [restaurantId, averageTicket]) => {
      if (averageTicket === null) {
        return highestAverage;
      }

      if (!highestAverage) {
        return { restaurantId, averageTicket };
      }

      return averageTicket > highestAverage.averageTicket ? { restaurantId, averageTicket } : highestAverage;
    },
    undefined,
  );
}

export function findRestaurantWithLowestAverageTicket(sales: readonly Sale[]): RestaurantAverageTicket | undefined {
  const averagesByRestaurant = calculateAverageTicketByRestaurant(sales);

  return Object.entries(averagesByRestaurant).reduce<RestaurantAverageTicket | undefined>(
    (lowestAverage, [restaurantId, averageTicket]) => {
      if (averageTicket === null) {
        return lowestAverage;
      }

      if (!lowestAverage) {
        return { restaurantId, averageTicket };
      }

      return averageTicket < lowestAverage.averageTicket ? { restaurantId, averageTicket } : lowestAverage;
    },
    undefined,
  );
}
