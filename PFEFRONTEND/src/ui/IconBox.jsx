/**
 * Shared coral icon box — same visual language as Edit AI Target / Assessment Versions.
 */
export function IconBox({ children, className = '', size = 'md' }) {
  const sizeClass = size === 'sm' ? ' iconBoxSm' : size === 'lg' ? ' iconBoxLg' : ''
  return (
    <span className={`iconBox${sizeClass}${className ? ` ${className}` : ''}`} aria-hidden="true">
      {children}
    </span>
  )
}

/**
 * Section title with optional coral icon box (for page / panel headers).
 */
export function SectionHeading({
  icon: Icon,
  title,
  subtitle,
  titleId,
  as: Tag = 'h2',
  badge,
  className = '',
}) {
  return (
    <div className={`sectionHeadingWithIcon${className ? ` ${className}` : ''}`}>
      {Icon ? (
        <IconBox>
          <Icon size={22} strokeWidth={2.25} />
        </IconBox>
      ) : null}
      <div className="sectionHeadingText">
        <div className="sectionHeadingTitleRow">
          <Tag id={titleId} className="sectionTitle">
            {title}
          </Tag>
          {badge != null ? <div className="badge">{badge}</div> : null}
        </div>
        {subtitle ? <p className="sectionHint">{subtitle}</p> : null}
      </div>
    </div>
  )
}

/** Inline icon before button label — keeps English text. */
export function BtnIcon({ icon: Icon, size = 16 }) {
  if (!Icon) return null
  return <Icon className="btnIcon" size={size} strokeWidth={2.2} aria-hidden="true" />
}
