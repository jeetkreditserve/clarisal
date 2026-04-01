interface FieldErrorTextProps {
  message?: string
}

export function FieldErrorText({ message }: FieldErrorTextProps) {
  if (!message) return null

  return <p className="field-error">{message}</p>
}
