import './TraversalResultModal.css'

export type ClinicalDecisionSupportLocale = 'en' | 'vi'

const messages = {
  en: {
    recommendationTitle: 'Clinical decision support recommendation',
    whyTitle: 'Why did this alert fire?', noEvidence: 'No structured trigger evidence was provided.',
    recommendedAction: 'Recommended action', noRecommendation: 'Review the available clinical findings.',
    recommendationStrength: 'Recommendation strength', evidenceLevel: 'Evidence level',
    recommendedOrders: 'Recommended orders', startingDose: 'Starting dose',
    medicineName: 'Medicine', dose: 'Dose', noMedicines: 'No matching medicines are available.',
    additionalActions: 'Additional clinical actions',
    noAdditionalActions: 'No additional actions were provided.',
    fullDecisionPath: 'Full decision path', cancel: 'Close',
  },
  vi: {
    recommendationTitle: 'Khuyến nghị hỗ trợ quyết định lâm sàng',
    whyTitle: 'Tại sao cảnh báo này xuất hiện?', noEvidence: 'Không có bằng chứng kích hoạt có cấu trúc.',
    recommendedAction: 'Hành động được khuyến nghị', noRecommendation: 'Đánh giá các phát hiện lâm sàng hiện có.',
    recommendationStrength: 'Mức độ khuyến nghị', evidenceLevel: 'Mức độ bằng chứng',
    recommendedOrders: 'Chỉ định được khuyến nghị', startingDose: 'Liều khởi đầu',
    medicineName: 'Tên thuốc', dose: 'Liều', noMedicines: 'Không có thuốc phù hợp hiện có.',
    additionalActions: 'Hành động lâm sàng bổ sung',
    noAdditionalActions: 'Không có hành động bổ sung.',
    fullDecisionPath: 'Toàn bộ đường đi quyết định', cancel: 'Đóng',
  },
} as const

export function getClinicalDecisionSupportMessages(locale: ClinicalDecisionSupportLocale) { return messages[locale] }
