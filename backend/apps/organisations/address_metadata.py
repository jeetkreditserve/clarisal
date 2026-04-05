import re

from .country_metadata import DEFAULT_COUNTRY_CODE, get_country_metadata, normalize_country_code

SUBDIVISION_ROWS = """
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
""".strip()

COUNTRY_ADDRESS_RULES = {
    'IN': {
        'subdivision_label': 'State / union territory',
        'postal_label': 'PIN code',
        'postal_pattern': re.compile(r'^\d{6}$'),
        'postal_help_text': 'Use the 6-digit India PIN code.',
        'postal_required': True,
        'tax_label': 'GSTIN',
        'tax_pattern': re.compile(r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][1-9A-Z]Z[0-9A-Z]$'),
        'tax_help_text': 'Billing addresses in India must have a valid GSTIN that matches the organisation PAN and state.',
        'billing_tax_required': True,
    },
    'US': {
        'subdivision_label': 'State',
        'postal_label': 'ZIP code',
        'postal_pattern': re.compile(r'^\d{5}(?:-\d{4})?$'),
        'postal_help_text': 'Use 5 digits or ZIP+4.',
        'postal_required': True,
    },
    'CA': {
        'subdivision_label': 'Province / territory',
        'postal_label': 'Postal code',
        'postal_pattern': re.compile(r'^[A-Z]\d[A-Z][ -]?\d[A-Z]\d$', re.IGNORECASE),
        'postal_help_text': 'Use the Canadian postal code format, for example M5V 2T6.',
        'postal_required': True,
    },
    'AU': {
        'subdivision_label': 'State / territory',
        'postal_label': 'Postcode',
        'postal_pattern': re.compile(r'^\d{4}$'),
        'postal_help_text': 'Use the 4-digit Australian postcode.',
        'postal_required': True,
    },
    'AE': {
        'subdivision_label': 'Emirate',
        'postal_label': 'PO Box / postal code',
        'postal_pattern': None,
        'postal_help_text': '',
        'postal_required': False,
    },
    'SG': {
        'subdivision_label': 'Planning area',
        'postal_label': 'Postal code',
        'postal_pattern': re.compile(r'^\d{6}$'),
        'postal_help_text': 'Use the 6-digit Singapore postal code.',
        'postal_required': True,
    },
    'NZ': {
        'subdivision_label': 'Region',
        'postal_label': 'Postcode',
        'postal_pattern': re.compile(r'^\d{4}$'),
        'postal_help_text': 'Use the 4-digit New Zealand postcode.',
        'postal_required': True,
    },
    'ZA': {
        'subdivision_label': 'Province',
        'postal_label': 'Postal code',
        'postal_pattern': re.compile(r'^\d{4}$'),
        'postal_help_text': 'Use the 4-digit South African postal code.',
        'postal_required': True,
    },
    'GB': {
        'subdivision_label': 'County / region',
        'postal_label': 'Postcode',
        'postal_pattern': re.compile(r'^[A-Z]{1,2}\d[A-Z\d]?\s*\d[A-Z]{2}$', re.IGNORECASE),
        'postal_help_text': 'Use the UK postcode format, for example SW1A 1AA.',
        'postal_required': True,
    },
}

SUBDIVISIONS_BY_COUNTRY: dict[str, list[dict[str, str]]] = {}
for row in SUBDIVISION_ROWS.splitlines():
    country_code, code, label, *rest = row.split('|')
    SUBDIVISIONS_BY_COUNTRY.setdefault(country_code, []).append(
        {
            'code': code,
            'label': label,
            'tax_region_code': rest[0] if rest else '',
        }
    )

for subdivision_list in SUBDIVISIONS_BY_COUNTRY.values():
    subdivision_list.sort(key=lambda item: item['label'])


def get_country_rule(country_code=None):
    resolved_country_code = normalize_country_code(country_code or DEFAULT_COUNTRY_CODE)
    base_rule = COUNTRY_ADDRESS_RULES.get(resolved_country_code, {})
    return {
        'country_code': resolved_country_code,
        'subdivision_label': base_rule.get('subdivision_label', 'State / region'),
        'postal_label': base_rule.get('postal_label', 'Postal code'),
        'postal_pattern': base_rule.get('postal_pattern'),
        'postal_help_text': base_rule.get('postal_help_text', ''),
        'postal_required': base_rule.get('postal_required', True),
        'tax_label': base_rule.get('tax_label', 'Business tax ID'),
        'tax_pattern': base_rule.get('tax_pattern'),
        'tax_help_text': base_rule.get('tax_help_text', ''),
        'billing_tax_required': base_rule.get('billing_tax_required', False),
    }


def get_country_name(country_code=None):
    return get_country_metadata(country_code or DEFAULT_COUNTRY_CODE)['name']


def get_subdivision_options(country_code=None):
    resolved_country_code = normalize_country_code(country_code or DEFAULT_COUNTRY_CODE)
    return SUBDIVISIONS_BY_COUNTRY.get(resolved_country_code, [])


def get_subdivision(country_code=None, state_code=None, state_name=None):
    options = get_subdivision_options(country_code)
    if not options:
        return None
    if state_code:
        normalized_code = state_code.strip().upper()
        for option in options:
            if option['code'] == normalized_code:
                return option
    normalized_name = (state_name or '').strip().lower()
    if normalized_name:
        for option in options:
            if option['label'].lower() == normalized_name or option['code'].lower() == normalized_name:
                return option
    return None


def normalize_subdivision(country_code=None, state_code=None, state_name=None):
    options = get_subdivision_options(country_code)
    if not options:
        return ((state_code or '').strip().upper(), (state_name or '').strip())

    subdivision = get_subdivision(country_code, state_code=state_code, state_name=state_name)
    if subdivision is None:
        raise ValueError(f"Select a valid {get_country_rule(country_code)['subdivision_label'].lower()}.")
    return subdivision['code'], subdivision['label']


def validate_postal_code(postal_code, country_code=None):
    rule = get_country_rule(country_code)
    normalized_postal_code = (postal_code or '').strip()
    if not normalized_postal_code:
        if rule['postal_required']:
            raise ValueError(f"{rule['postal_label']} is required.")
        return ''
    if rule['postal_pattern'] and not rule['postal_pattern'].match(normalized_postal_code):
        raise ValueError(rule['postal_help_text'] or f"Enter a valid {rule['postal_label'].lower()}.")
    return normalized_postal_code


def validate_billing_tax_identifier(*, country_code=None, address_type=None, identifier=None, pan_number='', state_code=''):
    rule = get_country_rule(country_code)
    normalized_identifier = (identifier or '').replace(' ', '').upper()
    requires_tax = address_type == 'BILLING' and rule['billing_tax_required']

    if not normalized_identifier:
        if requires_tax:
            raise ValueError(f"{rule['tax_label']} is required for the billing address.")
        return None

    if rule['tax_pattern'] and not rule['tax_pattern'].match(normalized_identifier):
        raise ValueError(rule['tax_help_text'] or f"Enter a valid {rule['tax_label']}.")

    if normalize_country_code(country_code or DEFAULT_COUNTRY_CODE) == 'IN':
        normalized_pan = (pan_number or '').replace(' ', '').upper()
        if normalized_pan and normalized_identifier[2:12] != normalized_pan:
            raise ValueError('GSTIN must contain the organisation PAN number.')
        subdivision = get_subdivision(country_code, state_code=state_code)
        if subdivision and subdivision.get('tax_region_code') and normalized_identifier[:2] != subdivision['tax_region_code']:
            raise ValueError(
                f"GSTIN must start with {subdivision['tax_region_code']} for {subdivision['label']}."
            )

    return normalized_identifier
