import { Customer, Restaurant, Sale, Supplier, SupplierPriceRecord } from "../types/models";

export function findRestaurantById(restaurants: readonly Restaurant[], restaurantId: string): Restaurant | undefined {
  return restaurants.find((restaurant) => restaurant.id === restaurantId);
}

export function findSupplierByName(suppliers: readonly Supplier[], supplierName: string): Supplier | undefined {
  const normalizedName = supplierName.trim().toLowerCase();
  return suppliers.find((supplier) => supplier.name.trim().toLowerCase() === normalizedName);
}

export function findCustomerByEmail(customers: readonly Customer[], email: string): Customer | undefined {
  const normalizedEmail = email.trim().toLowerCase();
  return customers.find((customer) => customer.email.trim().toLowerCase() === normalizedEmail);
}

export function binarySearchSaleByTotalAmount(sortedSales: readonly Sale[], targetAmount: number): Sale | undefined {
  if (sortedSales.length === 0) {
    return undefined;
  }

  let leftIndex = 0;
  let rightIndex = sortedSales.length - 1;

  // Requiere arreglo ordenado por sale.total.amount en orden ascendente.
  while (leftIndex <= rightIndex) {
    const middleIndex = Math.floor((leftIndex + rightIndex) / 2);
    const middleAmount = sortedSales[middleIndex].total.amount;

    if (middleAmount === targetAmount) {
      return sortedSales[middleIndex];
    }

    if (middleAmount < targetAmount) {
      leftIndex = middleIndex + 1;
    } else {
      rightIndex = middleIndex - 1;
    }
  }

  return undefined;
}

export function binarySearchSupplierPriceByIngredientName(
  sortedPriceHistory: readonly SupplierPriceRecord[],
  ingredientName: string,
): SupplierPriceRecord | undefined {
  if (sortedPriceHistory.length === 0) {
    return undefined;
  }

  const normalizedIngredientName = ingredientName.trim().toLowerCase();
  let leftIndex = 0;
  let rightIndex = sortedPriceHistory.length - 1;

  // Requiere arreglo ordenado por ingredientName en orden ascendente.
  while (leftIndex <= rightIndex) {
    const middleIndex = Math.floor((leftIndex + rightIndex) / 2);
    const middleIngredientName = sortedPriceHistory[middleIndex].ingredientName.trim().toLowerCase();
    const comparison = middleIngredientName.localeCompare(normalizedIngredientName);

    if (comparison === 0) {
      return sortedPriceHistory[middleIndex];
    }

    if (comparison < 0) {
      leftIndex = middleIndex + 1;
    } else {
      rightIndex = middleIndex - 1;
    }
  }

  return undefined;
}
