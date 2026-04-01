import {
  COUNTRY_OPTIONS,
  DEFAULT_COUNTRY_CODE,
  DEFAULT_COUNTRY_OPTION,
  getCountryOption,
  type CountryOption,
} from '@/lib/organisationMetadata'

export interface AddressSubdivisionOption {
  code: string
  label: string
  taxRegionCode?: string
}

export interface AddressCountryRule {
  countryCode: string
  subdivisionLabel: string
  postalLabel: string
  postalPlaceholder: string
  postalRegex?: RegExp
  postalHelperText?: string
  postalRequired?: boolean
  taxLabel?: string
  taxPlaceholder?: string
  taxHelperText?: string
  billingTaxRequired?: boolean
}

const SUBDIVISION_ROWS = `
IN|AN|Andaman and Nicobar Islands|35
IN|AP|Andhra Pradesh|37
IN|AR|Arunachal Pradesh|12
IN|AS|Assam|18
IN|BR|Bihar|10
IN|CH|Chandigarh|04
IN|CT|Chhattisgarh|22
IN|DH|Dadra and Nagar Haveli and Daman and Diu|26
IN|DL|Delhi|07
IN|GA|Goa|30
IN|GJ|Gujarat|24
IN|HR|Haryana|06
IN|HP|Himachal Pradesh|02
IN|JK|Jammu and Kashmir|01
IN|JH|Jharkhand|20
IN|KA|Karnataka|29
IN|KL|Kerala|32
IN|LA|Ladakh|38
IN|LD|Lakshadweep|31
IN|MP|Madhya Pradesh|23
IN|MH|Maharashtra|27
IN|MN|Manipur|14
IN|ML|Meghalaya|17
IN|MZ|Mizoram|15
IN|NL|Nagaland|13
IN|OD|Odisha|21
IN|PY|Puducherry|34
IN|PB|Punjab|03
IN|RJ|Rajasthan|08
IN|SK|Sikkim|11
IN|TN|Tamil Nadu|33
IN|TG|Telangana|36
IN|TR|Tripura|16
IN|UP|Uttar Pradesh|09
IN|UT|Uttarakhand|05
IN|WB|West Bengal|19
US|AL|Alabama
US|AK|Alaska
US|AZ|Arizona
US|AR|Arkansas
US|CA|California
US|CO|Colorado
US|CT|Connecticut
US|DE|Delaware
US|FL|Florida
US|GA|Georgia
US|HI|Hawaii
US|ID|Idaho
US|IL|Illinois
US|IN|Indiana
US|IA|Iowa
US|KS|Kansas
US|KY|Kentucky
US|LA|Louisiana
US|ME|Maine
US|MD|Maryland
US|MA|Massachusetts
US|MI|Michigan
US|MN|Minnesota
US|MS|Mississippi
US|MO|Missouri
US|MT|Montana
US|NE|Nebraska
US|NV|Nevada
US|NH|New Hampshire
US|NJ|New Jersey
US|NM|New Mexico
US|NY|New York
US|NC|North Carolina
US|ND|North Dakota
US|OH|Ohio
US|OK|Oklahoma
US|OR|Oregon
US|PA|Pennsylvania
US|RI|Rhode Island
US|SC|South Carolina
US|SD|South Dakota
US|TN|Tennessee
US|TX|Texas
US|UT|Utah
US|VT|Vermont
US|VA|Virginia
US|WA|Washington
US|WV|West Virginia
US|WI|Wisconsin
US|WY|Wyoming
US|DC|District of Columbia
CA|AB|Alberta
CA|BC|British Columbia
CA|MB|Manitoba
CA|NB|New Brunswick
CA|NL|Newfoundland and Labrador
CA|NS|Nova Scotia
CA|NT|Northwest Territories
CA|NU|Nunavut
CA|ON|Ontario
CA|PE|Prince Edward Island
CA|QC|Quebec
CA|SK|Saskatchewan
CA|YT|Yukon
AU|ACT|Australian Capital Territory
AU|NSW|New South Wales
AU|NT|Northern Territory
AU|QLD|Queensland
AU|SA|South Australia
AU|TAS|Tasmania
AU|VIC|Victoria
AU|WA|Western Australia
AE|AZ|Abu Dhabi
AE|AJ|Ajman
AE|DU|Dubai
AE|FU|Fujairah
AE|RK|Ras Al Khaimah
AE|SH|Sharjah
AE|UQ|Umm Al Quwain
NZ|AUK|Auckland
NZ|BOP|Bay of Plenty
NZ|CAN|Canterbury
NZ|GIS|Gisborne
NZ|HKB|Hawke's Bay
NZ|MWT|Manawatu-Whanganui
NZ|MBH|Marlborough
NZ|NSN|Nelson
NZ|NTL|Northland
NZ|OTA|Otago
NZ|STL|Southland
NZ|TKI|Taranaki
NZ|TAS|Tasman
NZ|WKO|Waikato
NZ|WGN|Wellington
NZ|WTC|West Coast
ZA|EC|Eastern Cape
ZA|FS|Free State
ZA|GP|Gauteng
ZA|KZN|KwaZulu-Natal
ZA|LP|Limpopo
ZA|MP|Mpumalanga
ZA|NC|Northern Cape
ZA|NW|North West
ZA|WC|Western Cape
`.trim()

const COUNTRY_RULES: Record<string, Omit<AddressCountryRule, 'countryCode'>> = {
  IN: {
    subdivisionLabel: 'State / union territory',
    postalLabel: 'PIN code',
    postalPlaceholder: '560001',
    postalRegex: /^\d{6}$/,
    postalHelperText: 'Use the 6-digit India PIN code.',
    taxLabel: 'GSTIN',
    taxPlaceholder: '29ABCDE1234F1Z5',
    taxHelperText: 'Billing addresses in India must have a valid GSTIN that matches the organisation PAN and state.',
    billingTaxRequired: true,
  },
  US: {
    subdivisionLabel: 'State',
    postalLabel: 'ZIP code',
    postalPlaceholder: '94105',
    postalRegex: /^\d{5}(?:-\d{4})?$/,
    postalHelperText: 'Use 5 digits or ZIP+4.',
  },
  CA: {
    subdivisionLabel: 'Province / territory',
    postalLabel: 'Postal code',
    postalPlaceholder: 'M5V 2T6',
    postalRegex: /^[A-Z]\d[A-Z][ -]?\d[A-Z]\d$/i,
    postalHelperText: 'Use the Canadian postal code format, for example M5V 2T6.',
  },
  AU: {
    subdivisionLabel: 'State / territory',
    postalLabel: 'Postcode',
    postalPlaceholder: '2000',
    postalRegex: /^\d{4}$/,
    postalHelperText: 'Use the 4-digit Australian postcode.',
  },
  AE: {
    subdivisionLabel: 'Emirate',
    postalLabel: 'PO Box / postal code',
    postalPlaceholder: '00000',
    postalRequired: false,
  },
  SG: {
    subdivisionLabel: 'Planning area',
    postalLabel: 'Postal code',
    postalPlaceholder: '018956',
    postalRegex: /^\d{6}$/,
    postalHelperText: 'Use the 6-digit Singapore postal code.',
  },
  NZ: {
    subdivisionLabel: 'Region',
    postalLabel: 'Postcode',
    postalPlaceholder: '1010',
    postalRegex: /^\d{4}$/,
    postalHelperText: 'Use the 4-digit New Zealand postcode.',
  },
  ZA: {
    subdivisionLabel: 'Province',
    postalLabel: 'Postal code',
    postalPlaceholder: '2196',
    postalRegex: /^\d{4}$/,
    postalHelperText: 'Use the 4-digit South African postal code.',
  },
  GB: {
    subdivisionLabel: 'County / region',
    postalLabel: 'Postcode',
    postalPlaceholder: 'SW1A 1AA',
    postalRegex:
      /^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$/i,
    postalHelperText: 'Use the UK postcode format, for example SW1A 1AA.',
  },
}

const subdivisionRows = SUBDIVISION_ROWS.split('\n').map((row) => {
  const [countryCode, code, label, taxRegionCode] = row.split('|')
  return { countryCode, code, label, taxRegionCode }
})

export const ADDRESS_SUBDIVISIONS_BY_COUNTRY = subdivisionRows.reduce<Record<string, AddressSubdivisionOption[]>>((accumulator, row) => {
  if (!accumulator[row.countryCode]) {
    accumulator[row.countryCode] = []
  }
  accumulator[row.countryCode].push({
    code: row.code,
    label: row.label,
    taxRegionCode: row.taxRegionCode || undefined,
  })
  return accumulator
}, {})

for (const subdivisions of Object.values(ADDRESS_SUBDIVISIONS_BY_COUNTRY)) {
  subdivisions.sort((left, right) => left.label.localeCompare(right.label))
}

const COUNTRY_OPTIONS_BY_NAME = COUNTRY_OPTIONS.reduce<Record<string, CountryOption>>((accumulator, country) => {
  accumulator[country.name.toLowerCase()] = country
  return accumulator
}, {})

export function getAddressCountryOption(codeOrName?: string | null): CountryOption | null {
  if (!codeOrName) return null
  const normalizedValue = codeOrName.trim()
  if (!normalizedValue) return null
  const byCode = getCountryOption(normalizedValue)
  if (byCode) return byCode
  return COUNTRY_OPTIONS_BY_NAME[normalizedValue.toLowerCase()] ?? null
}

export function resolveCountryCode(codeOrName?: string | null, fallbackCode = DEFAULT_COUNTRY_CODE) {
  return getAddressCountryOption(codeOrName)?.code ?? fallbackCode
}

export function getAddressCountryName(codeOrName?: string | null, fallbackName = DEFAULT_COUNTRY_OPTION.name) {
  return getAddressCountryOption(codeOrName)?.name ?? fallbackName
}

export function getAddressCountryRule(countryCode?: string | null): AddressCountryRule {
  const resolvedCountryCode = resolveCountryCode(countryCode)
  return {
    countryCode: resolvedCountryCode,
    subdivisionLabel: COUNTRY_RULES[resolvedCountryCode]?.subdivisionLabel ?? 'State / region',
    postalLabel: COUNTRY_RULES[resolvedCountryCode]?.postalLabel ?? 'Postal code',
    postalPlaceholder: COUNTRY_RULES[resolvedCountryCode]?.postalPlaceholder ?? '',
    postalRegex: COUNTRY_RULES[resolvedCountryCode]?.postalRegex,
    postalHelperText: COUNTRY_RULES[resolvedCountryCode]?.postalHelperText,
    postalRequired: COUNTRY_RULES[resolvedCountryCode]?.postalRequired ?? true,
    taxLabel: COUNTRY_RULES[resolvedCountryCode]?.taxLabel ?? 'Business tax ID',
    taxPlaceholder: COUNTRY_RULES[resolvedCountryCode]?.taxPlaceholder ?? '',
    taxHelperText: COUNTRY_RULES[resolvedCountryCode]?.taxHelperText,
    billingTaxRequired: COUNTRY_RULES[resolvedCountryCode]?.billingTaxRequired ?? false,
  }
}

export function getSubdivisionOptions(countryCode?: string | null) {
  return ADDRESS_SUBDIVISIONS_BY_COUNTRY[resolveCountryCode(countryCode)] ?? []
}

export function getSubdivisionOption(countryCode?: string | null, stateCode?: string | null) {
  if (!stateCode) return null
  return getSubdivisionOptions(countryCode).find((option) => option.code === stateCode) ?? null
}

export function resolveSubdivisionCode(countryCode?: string | null, stateValue?: string | null, stateCode?: string | null) {
  const options = getSubdivisionOptions(countryCode)
  if (options.length === 0) {
    return stateCode?.trim() ?? ''
  }
  if (stateCode) {
    const byCode = options.find((option) => option.code === stateCode)
    if (byCode) return byCode.code
  }
  const normalizedState = (stateValue ?? '').trim().toLowerCase()
  if (!normalizedState) return ''
  const byName = options.find(
    (option) => option.label.toLowerCase() === normalizedState || option.code.toLowerCase() === normalizedState,
  )
  return byName?.code ?? ''
}

export function getSubdivisionName(countryCode?: string | null, stateCode?: string | null, fallbackState = '') {
  return getSubdivisionOption(countryCode, stateCode)?.label ?? fallbackState
}

export function getPostalLabel(countryCode?: string | null) {
  return getAddressCountryRule(countryCode).postalLabel
}

export function validatePostalCodeForCountry(postalCode: string, countryCode?: string | null) {
  const rule = getAddressCountryRule(countryCode)
  const normalizedPostalCode = postalCode.trim()
  if (!normalizedPostalCode) {
    return rule.postalRequired === false ? null : `${rule.postalLabel} is required.`
  }
  if (rule.postalRegex && !rule.postalRegex.test(normalizedPostalCode)) {
    return rule.postalHelperText ?? `Enter a valid ${rule.postalLabel.toLowerCase()}.`
  }
  return null
}

export function getBillingTaxLabel(countryCode?: string | null) {
  return getAddressCountryRule(countryCode).taxLabel ?? 'Business tax ID'
}

export function isBillingTaxRequired(countryCode?: string | null) {
  return getAddressCountryRule(countryCode).billingTaxRequired === true
}

export function normalizeTaxIdentifier(value?: string | null) {
  return (value ?? '').replace(/\s+/g, '').toUpperCase()
}

export function validateBillingTaxIdentifier(params: {
  addressType?: string | null
  countryCode?: string | null
  stateCode?: string | null
  panNumber?: string | null
  identifier?: string | null
}) {
  const { addressType, countryCode, stateCode, panNumber, identifier } = params
  const rule = getAddressCountryRule(countryCode)
  const normalizedIdentifier = normalizeTaxIdentifier(identifier)
  const requiresTaxId = addressType === 'BILLING' && rule.billingTaxRequired

  if (!normalizedIdentifier) {
    return requiresTaxId ? `${rule.taxLabel ?? 'Business tax ID'} is required for the billing address.` : null
  }

  if (resolveCountryCode(countryCode) === 'IN') {
    if (!/^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$/.test(normalizedIdentifier)) {
      return 'GSTIN must be in the format 22AAAAA0000A1Z5.'
    }
    const normalizedPan = normalizeTaxIdentifier(panNumber)
    if (normalizedPan && normalizedIdentifier.slice(2, 12) !== normalizedPan) {
      return 'GSTIN must contain the organisation PAN number.'
    }
    const state = getSubdivisionOption(countryCode, stateCode)
    if (state?.taxRegionCode && normalizedIdentifier.slice(0, 2) !== state.taxRegionCode) {
      return `GSTIN must start with ${state.taxRegionCode} for ${state.label}.`
    }
  }

  return null
}
