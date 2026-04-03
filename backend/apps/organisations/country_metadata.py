import re

DEFAULT_COUNTRY_CODE = 'IN'
DEFAULT_CURRENCY_CODE = 'INR'

COUNTRY_METADATA_ROWS = """
AF|Afghanistan|+93|AFN
AX|Aland Islands|+358|EUR
AL|Albania|+355|ALL
DZ|Algeria|+213|DZD
AS|American Samoa|+1|USD
AD|Andorra|+376|EUR
AO|Angola|+244|AOA
AI|Anguilla|+1|XCD
AQ|Antarctica|+672|AAD
AG|Antigua and Barbuda|+1|XCD
AR|Argentina|+54|ARS
AM|Armenia|+374|AMD
AW|Aruba|+297|AWG
AU|Australia|+61|AUD
AT|Austria|+43|EUR
AZ|Azerbaijan|+994|AZN
BH|Bahrain|+973|BHD
BD|Bangladesh|+880|BDT
BB|Barbados|+1|BBD
BY|Belarus|+375|BYN
BE|Belgium|+32|EUR
BZ|Belize|+501|BZD
BJ|Benin|+229|XOF
BM|Bermuda|+1|BMD
BT|Bhutan|+975|BTN
BO|Bolivia|+591|BOB
BQ|Bonaire, Sint Eustatius and Saba|+599|USD
BA|Bosnia and Herzegovina|+387|BAM
BW|Botswana|+267|BWP
BV|Bouvet Island|+0055|NOK
BR|Brazil|+55|BRL
IO|British Indian Ocean Territory|+246|USD
BN|Brunei|+673|BND
BG|Bulgaria|+359|BGN
BF|Burkina Faso|+226|XOF
BI|Burundi|+257|BIF
KH|Cambodia|+855|KHR
CM|Cameroon|+237|XAF
CA|Canada|+1|CAD
CV|Cape Verde|+238|CVE
KY|Cayman Islands|+1|KYD
CF|Central African Republic|+236|XAF
TD|Chad|+235|XAF
CL|Chile|+56|CLP
CN|China|+86|CNY
CX|Christmas Island|+61|AUD
CC|Cocos (Keeling) Islands|+61|AUD
CO|Colombia|+57|COP
KM|Comoros|+269|KMF
CG|Congo|+242|CDF
CK|Cook Islands|+682|NZD
CR|Costa Rica|+506|CRC
HR|Croatia|+385|EUR
CU|Cuba|+53|CUP
CW|Curaçao|+599|ANG
CY|Cyprus|+357|EUR
CZ|Czech Republic|+420|CZK
CD|Democratic Republic of the Congo|+243|CDF
DK|Denmark|+45|DKK
DJ|Djibouti|+253|DJF
DM|Dominica|+1|XCD
DO|Dominican Republic|+1|DOP
EC|Ecuador|+593|USD
EG|Egypt|+20|EGP
SV|El Salvador|+503|USD
GQ|Equatorial Guinea|+240|XAF
ER|Eritrea|+291|ERN
EE|Estonia|+372|EUR
SZ|Eswatini|+268|SZL
ET|Ethiopia|+251|ETB
FK|Falkland Islands|+500|FKP
FO|Faroe Islands|+298|DKK
FJ|Fiji Islands|+679|FJD
FI|Finland|+358|EUR
FR|France|+33|EUR
GF|French Guiana|+594|EUR
PF|French Polynesia|+689|XPF
TF|French Southern Territories|+262|EUR
GA|Gabon|+241|XAF
GE|Georgia|+995|GEL
DE|Germany|+49|EUR
GH|Ghana|+233|GHS
GI|Gibraltar|+350|GIP
GR|Greece|+30|EUR
GL|Greenland|+299|DKK
GD|Grenada|+1|XCD
GP|Guadeloupe|+590|EUR
GU|Guam|+1|USD
GT|Guatemala|+502|GTQ
GG|Guernsey|+44|GBP
GN|Guinea|+224|GNF
GW|Guinea-Bissau|+245|XOF
GY|Guyana|+592|GYD
HT|Haiti|+509|HTG
HM|Heard Island and McDonald Islands|+672|AUD
HN|Honduras|+504|HNL
HK|Hong Kong S.A.R.|+852|HKD
HU|Hungary|+36|HUF
IS|Iceland|+354|ISK
IN|India|+91|INR
ID|Indonesia|+62|IDR
IR|Iran|+98|IRR
IQ|Iraq|+964|IQD
IE|Ireland|+353|EUR
IL|Israel|+972|ILS
IT|Italy|+39|EUR
CI|Ivory Coast|+225|XOF
JM|Jamaica|+1|JMD
JP|Japan|+81|JPY
JE|Jersey|+44|GBP
JO|Jordan|+962|JOD
KZ|Kazakhstan|+7|KZT
KE|Kenya|+254|KES
KI|Kiribati|+686|AUD
XK|Kosovo|+383|EUR
KW|Kuwait|+965|KWD
KG|Kyrgyzstan|+996|KGS
LA|Laos|+856|LAK
LV|Latvia|+371|EUR
LB|Lebanon|+961|LBP
LS|Lesotho|+266|LSL
LR|Liberia|+231|LRD
LY|Libya|+218|LYD
LI|Liechtenstein|+423|CHF
LT|Lithuania|+370|EUR
LU|Luxembourg|+352|EUR
MO|Macau S.A.R.|+853|MOP
MG|Madagascar|+261|MGA
MW|Malawi|+265|MWK
MY|Malaysia|+60|MYR
MV|Maldives|+960|MVR
ML|Mali|+223|XOF
MT|Malta|+356|EUR
IM|Man (Isle of)|+44|GBP
MH|Marshall Islands|+692|USD
MQ|Martinique|+596|EUR
MR|Mauritania|+222|MRU
MU|Mauritius|+230|MUR
YT|Mayotte|+262|EUR
MX|Mexico|+52|MXN
FM|Micronesia|+691|USD
MD|Moldova|+373|MDL
MC|Monaco|+377|EUR
MN|Mongolia|+976|MNT
ME|Montenegro|+382|EUR
MS|Montserrat|+1|XCD
MA|Morocco|+212|MAD
MZ|Mozambique|+258|MZN
MM|Myanmar|+95|MMK
NA|Namibia|+264|NAD
NR|Nauru|+674|AUD
NP|Nepal|+977|NPR
NL|Netherlands|+31|EUR
NC|New Caledonia|+687|XPF
NZ|New Zealand|+64|NZD
NI|Nicaragua|+505|NIO
NE|Niger|+227|XOF
NG|Nigeria|+234|NGN
NU|Niue|+683|NZD
NF|Norfolk Island|+672|AUD
KP|North Korea|+850|KPW
MK|North Macedonia|+389|MKD
MP|Northern Mariana Islands|+1|USD
NO|Norway|+47|NOK
OM|Oman|+968|OMR
PK|Pakistan|+92|PKR
PW|Palau|+680|USD
PS|Palestinian Territory Occupied|+970|ILS
PA|Panama|+507|PAB
PG|Papua New Guinea|+675|PGK
PY|Paraguay|+595|PYG
PE|Peru|+51|PEN
PH|Philippines|+63|PHP
PN|Pitcairn Island|+870|NZD
PL|Poland|+48|PLN
PT|Portugal|+351|EUR
PR|Puerto Rico|+1|USD
QA|Qatar|+974|QAR
RE|Reunion|+262|EUR
RO|Romania|+40|RON
RU|Russia|+7|RUB
RW|Rwanda|+250|RWF
SH|Saint Helena|+290|SHP
KN|Saint Kitts and Nevis|+1|XCD
LC|Saint Lucia|+1|XCD
PM|Saint Pierre and Miquelon|+508|EUR
VC|Saint Vincent and the Grenadines|+1|XCD
BL|Saint-Barthelemy|+590|EUR
MF|Saint-Martin (French part)|+590|EUR
WS|Samoa|+685|WST
SM|San Marino|+378|EUR
ST|Sao Tome and Principe|+239|STN
SA|Saudi Arabia|+966|SAR
SN|Senegal|+221|XOF
RS|Serbia|+381|RSD
SC|Seychelles|+248|SCR
SL|Sierra Leone|+232|SLL
SG|Singapore|+65|SGD
SX|Sint Maarten (Dutch part)|+1721|ANG
SK|Slovakia|+421|EUR
SI|Slovenia|+386|EUR
SB|Solomon Islands|+677|SBD
SO|Somalia|+252|SOS
ZA|South Africa|+27|ZAR
GS|South Georgia|+500|GBP
KR|South Korea|+82|KRW
SS|South Sudan|+211|SSP
ES|Spain|+34|EUR
LK|Sri Lanka|+94|LKR
SD|Sudan|+249|SDG
SR|Suriname|+597|SRD
SJ|Svalbard and Jan Mayen Islands|+47|NOK
SE|Sweden|+46|SEK
CH|Switzerland|+41|CHF
SY|Syria|+963|SYP
TW|Taiwan|+886|TWD
TJ|Tajikistan|+992|TJS
TZ|Tanzania|+255|TZS
TH|Thailand|+66|THB
BS|The Bahamas|+1|BSD
GM|The Gambia|+220|GMD
TL|Timor-Leste|+670|USD
TG|Togo|+228|XOF
TK|Tokelau|+690|NZD
TO|Tonga|+676|TOP
TT|Trinidad and Tobago|+1|TTD
TN|Tunisia|+216|TND
TR|Turkey|+90|TRY
TM|Turkmenistan|+993|TMT
TC|Turks and Caicos Islands|+1|USD
TV|Tuvalu|+688|AUD
UG|Uganda|+256|UGX
UA|Ukraine|+380|UAH
AE|United Arab Emirates|+971|AED
GB|United Kingdom|+44|GBP
US|United States|+1|USD
UM|United States Minor Outlying Islands|+1|USD
UY|Uruguay|+598|UYU
UZ|Uzbekistan|+998|UZS
VU|Vanuatu|+678|VUV
VA|Vatican City State (Holy See)|+379|EUR
VE|Venezuela|+58|VES
VN|Vietnam|+84|VND
VG|Virgin Islands (British)|+1|USD
VI|Virgin Islands (US)|+1|USD
WF|Wallis and Futuna Islands|+681|XPF
EH|Western Sahara|+212|MAD
YE|Yemen|+967|YER
ZM|Zambia|+260|ZMW
ZW|Zimbabwe|+263|ZWL
""".strip()


COUNTRY_METADATA = {}
for row in COUNTRY_METADATA_ROWS.splitlines():
    code, name, dial_code, default_currency = row.split('|')
    COUNTRY_METADATA[code] = {
        'code': code,
        'name': name,
        'dial_code': dial_code,
        'default_currency': default_currency,
    }

SUPPORTED_COUNTRY_CODES = frozenset(COUNTRY_METADATA.keys())
COUNTRY_CODES_BY_NAME = {
    metadata['name'].lower(): metadata['code']
    for metadata in COUNTRY_METADATA.values()
}
SUPPORTED_CURRENCY_CODES = frozenset(
    metadata['default_currency']
    for metadata in COUNTRY_METADATA.values()
)


def get_country_metadata(code):
    country_code = normalize_country_code(code)
    return COUNTRY_METADATA[country_code]


def normalize_country_code(value):
    country_code = (value or '').strip().upper()
    if country_code not in SUPPORTED_COUNTRY_CODES:
        raise ValueError('Select a valid country.')
    return country_code


def resolve_country_code(value):
    raw_value = (value or '').strip()
    if not raw_value:
        return DEFAULT_COUNTRY_CODE
    upper_value = raw_value.upper()
    if upper_value in SUPPORTED_COUNTRY_CODES:
        return upper_value
    by_name = COUNTRY_CODES_BY_NAME.get(raw_value.lower())
    if by_name:
        return by_name
    raise ValueError('Select a valid country.')


def normalize_currency_code(value):
    currency_code = (value or '').strip().upper()
    if currency_code not in SUPPORTED_CURRENCY_CODES:
        raise ValueError('Select a valid currency.')
    return currency_code


def normalize_phone_number(value):
    raw_value = (value or '').strip()
    if not raw_value:
        return ''
    cleaned = re.sub(r'[\s\-()]+', '', raw_value)
    if not cleaned.startswith('+'):
        raise ValueError('Phone number must include the country dial code prefix, for example +91.')
    if not re.fullmatch(r'\+\d+', cleaned):
        raise ValueError('Phone number must contain only digits after the + prefix.')
    return cleaned


def validate_phone_for_country(value, country_code):
    normalized_phone = normalize_phone_number(value)
    if not normalized_phone:
        return ''
    country = get_country_metadata(country_code)
    if not normalized_phone.startswith(country['dial_code']):
        raise ValueError(
            f"Phone number must start with {country['dial_code']} for {country['name']}."
        )
    return normalized_phone
