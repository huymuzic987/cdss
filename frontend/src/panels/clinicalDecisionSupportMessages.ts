import './TraversalResultModal.css'

export type ClinicalDecisionSupportLocale = 'en' | 'vi'

const messages = {
  en: {
    recommendationTitle: 'Clinical decision support recommendation',
    alertSummary: 'Alert summary',
    critical: 'Critical',
    genericAlertSummary: 'Patient has clinical findings requiring review.',
    whyTitle: 'Why is this alert fired?', noEvidence: 'No structured trigger evidence was provided.',
    recommendedAction: 'Recommended action', noRecommendation: 'Review the available clinical findings.',
    recommendationStrength: 'Recommendation strength', evidenceLevel: 'Evidence level',
    recommendedOrders: 'Recommended orders', startingDose: 'Starting dose',
    medicineName: 'Medicine', dose: 'Dose', guidelineSource: 'Guideline source',
    section: 'Section',
    noMedicines: 'No matching medicines are available.',
    fullDecisionPath: 'Full decision path', cancel: 'Close',
  },
  vi: {
    recommendationTitle: 'Khuyến nghị hỗ trợ quyết định lâm sàng',
    alertSummary: 'Tóm tắt cảnh báo',
    critical: 'Cấp cứu',
    genericAlertSummary: 'Bệnh nhân có các phát hiện lâm sàng cần được đánh giá.',
    whyTitle: 'Tại sao cảnh báo này xuất hiện?', noEvidence: 'Không có bằng chứng kích hoạt có cấu trúc.',
    recommendedAction: 'Hành động được khuyến nghị', noRecommendation: 'Đánh giá các phát hiện lâm sàng hiện có.',
    recommendationStrength: 'Mức độ khuyến nghị', evidenceLevel: 'Mức độ bằng chứng',
    recommendedOrders: 'Chỉ định được khuyến nghị', startingDose: 'Liều khởi đầu',
    medicineName: 'Tên thuốc', dose: 'Liều', guidelineSource: 'Nguồn hướng dẫn',
    section: 'Mục',
    noMedicines: 'Không có thuốc phù hợp hiện có.',
    fullDecisionPath: 'Toàn bộ đường đi quyết định', cancel: 'Đóng',
  },
} as const

export function getClinicalDecisionSupportMessages(locale: ClinicalDecisionSupportLocale) { return messages[locale] }
