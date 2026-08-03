import type { FinalRegimenComponent, RegimenMedicine } from '../clinicalPresentation/types'
import { activeDose, componentMedicines, GROUP_NAMES, isSpecific } from './RegimenCatalog'

export function ComponentCatalogDetails({
  component, catalog, placement, position, onClose,
}: {
  component: FinalRegimenComponent
  catalog: Record<string, RegimenMedicine[]>
  placement: 'above' | 'below'
  position: { left: number, top: number }
  onClose: () => void
}) {
  const isSpecificMedicine = isSpecific(component)
  const medicines = componentMedicines(component, catalog)
  const subgroups = Array.from(new Set(medicines.map((medicine) => medicine.subgroup).filter(Boolean)))
  return (
    <div
      className={`cds-regimen-catalog-details cds-regimen-catalog-${placement}`}
      role="dialog"
      aria-label={`${component.label} drug details`}
      style={position}
    >
      <div className="cds-regimen-catalog-heading">
        <span>
          <strong>{component.label}{isSpecificMedicine ? '' : `: ${GROUP_NAMES[component.group]}`}</strong>
          {!isSpecificMedicine && subgroups.length > 0 && <small>Includes: {subgroups.join(' / ')}</small>}
        </span>
        <button type="button" onClick={onClose} aria-label="Close drug details">×</button>
      </div>
      {isSpecificMedicine && <span>Drug group: <b>{component.group}</b> · {GROUP_NAMES[component.group]}</span>}
      {medicines.length === 0 ? (
        <small>No catalogued medicines are available for this group.</small>
      ) : medicines.map((medicine) => (
        <div className="cds-regimen-medicine-detail" key={medicine.id || medicine.name}>
          <div className="cds-regimen-medicine-heading">
            {!isSpecificMedicine && <strong>{medicine.name}</strong>}
            <span>{medicine.route || 'Route not recorded'} / SNOMED CT: {medicine.snomedCode || 'Not recorded'}</span>
          </div>
          <div className="cds-regimen-dose-comparison">
            <span className={activeDose(component.dose) === 'low' ? 'cds-active-dose' : ''}>
              Low: {medicine.doseLow || '-'}
            </span>
            <span className={activeDose(component.dose) === 'usual' ? 'cds-active-dose' : ''}>
              Usual: {medicine.doseUsual || '-'}
            </span>
            <span className={activeDose(component.dose) === 'max' ? 'cds-active-dose' : ''}>
              Maximum: {medicine.doseMax || '-'}
            </span>
          </div>
        </div>
      ))}
    </div>
  )
}
