import './TraversalResultModal.css'

export type ClinicalDecisionSupportLocale = 'en' | 'vi'

const messages = {
  en: {
    title: 'Clinical Decision Support Result', incompleteTitle: 'Incomplete Decision Support Result',
    alertLabel: 'Patient-specific alert', defaultAlert: 'The available patient data triggered a clinical decision support rule.',
    whyTitle: 'Why did this alert fire?', noEvidence: 'No structured trigger evidence was provided.',
    recommendedAction: 'Recommended action', noRecommendation: 'Review the available clinical findings.',
    viewGuideline: 'View guideline', recommendationStrength: 'Recommendation strength', evidenceLevel: 'Evidence level',
    recommendedOrders: 'Recommended order options', noOrders: 'No order options were provided for this recommendation.',
    startingDose: 'Starting dose', selectClass: (label: string) => `Select ${label}`,
    order: 'Order', doNotOrder: 'Do not order', additionalActions: 'Additional clinical actions',
    noAdditionalActions: 'No additional actions were provided.', acknowledgementReason: 'Acknowledgement reason',
    acknowledgementHelp: 'Select a reason before saving a declined or deferred recommendation.',
    differentOrder: 'Will place a different order or use a different dose', discussPatient: 'Will discuss with patient',
    reviewChart: 'Will review chart', remindNextVisit: 'Remind me next visit', other: 'Other', otherReason: 'Other reason',
    reasonRequired: 'Select an acknowledgement reason to continue.', otherRequired: 'Enter the acknowledgement reason to continue.',
    clinicalDetails: 'Clinical details', fullDecisionPath: 'Full decision path', derivedContext: 'Derived context',
    conditionChecks: 'Condition checks', cancel: 'Cancel', acknowledge: 'Acknowledge / Save decision',
    acceptOrders: 'Accept and place orders',
  },
  vi: {
    title: 'Kết quả hỗ trợ quyết định lâm sàng', incompleteTitle: 'Kết quả hỗ trợ quyết định chưa hoàn tất',
    alertLabel: 'Cảnh báo theo bệnh nhân', defaultAlert: 'Dữ liệu hiện có của bệnh nhân đã kích hoạt một quy tắc hỗ trợ quyết định lâm sàng.',
    whyTitle: 'Tại sao cảnh báo này xuất hiện?', noEvidence: 'Không có bằng chứng kích hoạt có cấu trúc.',
    recommendedAction: 'Hành động được khuyến nghị', noRecommendation: 'Đánh giá các phát hiện lâm sàng hiện có.',
    viewGuideline: 'Xem hướng dẫn', recommendationStrength: 'Mức độ khuyến nghị', evidenceLevel: 'Mức độ bằng chứng',
    recommendedOrders: 'Các lựa chọn chỉ định được khuyến nghị', noOrders: 'Không có lựa chọn chỉ định cho khuyến nghị này.',
    startingDose: 'Liều khởi đầu', selectClass: (label: string) => `Chọn ${label}`,
    order: 'Chỉ định', doNotOrder: 'Không chỉ định', additionalActions: 'Hành động lâm sàng bổ sung',
    noAdditionalActions: 'Không có hành động bổ sung.', acknowledgementReason: 'Lý do xác nhận',
    acknowledgementHelp: 'Chọn lý do trước khi lưu quyết định từ chối hoặc trì hoãn.',
    differentOrder: 'Sẽ tạo chỉ định khác hoặc sử dụng liều khác', discussPatient: 'Sẽ trao đổi với bệnh nhân',
    reviewChart: 'Sẽ xem lại hồ sơ', remindNextVisit: 'Nhắc tôi ở lần khám sau', other: 'Khác', otherReason: 'Lý do khác',
    reasonRequired: 'Vui lòng chọn lý do xác nhận để tiếp tục.', otherRequired: 'Vui lòng nhập lý do xác nhận để tiếp tục.',
    clinicalDetails: 'Chi tiết lâm sàng', fullDecisionPath: 'Toàn bộ đường đi quyết định', derivedContext: 'Ngữ cảnh suy luận',
    conditionChecks: 'Các điều kiện đã kiểm tra', cancel: 'Hủy', acknowledge: 'Xác nhận / Lưu quyết định',
    acceptOrders: 'Chấp nhận và tạo chỉ định',
  },
} as const

export function getClinicalDecisionSupportMessages(locale: ClinicalDecisionSupportLocale) { return messages[locale] }
