export function isSingleMedicationOrder(order: {
  orderType?: string
  drugClasses?: Array<{ code: string }>
}): boolean {
  const isAbcdCombination = (order.drugClasses?.length ?? 0) > 1
    && order.drugClasses!.every((item) => /^[ABCD]$/.test(item.code))
  return order.orderType === 'medication' && !isAbcdCombination
}
