export type EmploymentType = 'FULL_TIME' | 'PART_TIME' | 'CONTRACT' | 'INTERN'
export type EmployeeStatus = 'INVITED' | 'PENDING' | 'ACTIVE' | 'RESIGNED' | 'RETIRED' | 'TERMINATED'
export type GovernmentIdType = 'PAN' | 'AADHAAR'
export type GovernmentIdStatus = 'PENDING' | 'VERIFIED' | 'REJECTED'
export type BankAccountType = 'SAVINGS' | 'CURRENT' | 'SALARY'
export type DocumentStatus = 'PENDING' | 'VERIFIED' | 'REJECTED'
export type DocumentType = 'PAN' | 'AADHAAR' | 'EDUCATION_CERT' | 'EMPLOYMENT_LETTER' | 'OTHER'

export interface LinkedOrganisationAddress {
  id: string
  address_type: string
  address_type_label: string
  label: string
  line1: string
  line2: string
  city: string
  state: string
  country: string
  pincode: string
  gstin: string | null
  is_active: boolean
}

export interface Location {
  id: string
  name: string
  organisation_address: LinkedOrganisationAddress | null
  organisation_address_id: string | null
  address: string
  city: string
  state: string
  country: string
  pincode: string
  is_remote: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface Department {
  id: string
  name: string
  description: string
  parent_department_id: string | null
  parent_department_name: string | null
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface EmployeeListItem {
  id: string
  employee_code: string | null
  full_name: string
  email: string
  designation: string
  employment_type: EmploymentType
  date_of_joining: string | null
  status: EmployeeStatus
  department_name: string | null
  office_location_name: string | null
}

export interface EmployeeProfile {
  date_of_birth?: string | null
  gender?: string
  marital_status?: string
  nationality?: string
  phone_personal?: string
  phone_emergency?: string
  emergency_contact_name?: string
  emergency_contact_relation?: string
  address_line1?: string
  address_line2?: string
  city?: string
  state?: string
  country?: string
  pincode?: string
}

export interface EducationRecord {
  id: string
  degree: string
  institution: string
  field_of_study: string
  start_year: number | null
  end_year: number | null
  grade: string
  is_current: boolean
  created_at: string
  updated_at: string
}

export interface GovernmentId {
  id: string
  id_type: GovernmentIdType
  identifier: string
  name_on_id: string
  status: GovernmentIdStatus
  metadata: Record<string, unknown>
  created_at: string
  updated_at: string
}

export interface BankAccount {
  id: string
  account_holder_name: string
  bank_name: string
  account_number: string
  ifsc: string
  account_type: BankAccountType
  branch_name: string
  is_primary: boolean
  created_at: string
  updated_at: string
}

export interface EmployeeDetail {
  id: string
  employee_code: string | null
  suggested_employee_code: string
  full_name: string
  email: string
  designation: string
  employment_type: EmploymentType
  date_of_joining: string | null
  date_of_exit: string | null
  status: EmployeeStatus
  department: string | null
  office_location: string | null
  profile: EmployeeProfile
  education_records: EducationRecord[]
  government_ids: GovernmentId[]
  bank_accounts: BankAccount[]
}

export interface ProfileCompletion {
  percent: number
  completed_sections: string[]
  missing_sections: string[]
}

export interface EmployeeDashboard {
  profile_completion: ProfileCompletion
  pending_documents: number
  verified_documents: number
  rejected_documents: number
  employee_code: string
}

export interface MyProfileResponse {
  employee: EmployeeDetail
  profile: EmployeeProfile
  profile_completion: ProfileCompletion
}

export interface DocumentRecord {
  id: string
  document_type: DocumentType
  file_name: string
  file_size: number
  mime_type: string
  status: DocumentStatus
  metadata: Record<string, unknown>
  uploaded_by_email: string | null
  reviewed_by_email: string | null
  reviewed_at: string | null
  created_at: string
}
