interface InfoTooltipProps {
  text: string
}

/** Dotted-underline label affix that reveals a plain-language explanation on
 * hover/focus -- no icon, so it doesn't add to icon clutter elsewhere on the
 * dashboard. Keyboard accessible via tabIndex + :focus-within. */
export function InfoTooltip({ text }: InfoTooltipProps) {
  return (
    <span className="dash-info" tabIndex={0}>
      <span className="dash-info-trigger">?</span>
      <span className="dash-info-popover">{text}</span>
    </span>
  )
}
