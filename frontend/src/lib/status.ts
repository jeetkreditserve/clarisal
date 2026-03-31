import type {
  ApprovalActionStatus,
  DocumentStatus,
  EmployeeDocumentRequestStatus,
  EmployeeOnboardingStatus,
  EmployeeStatus,
  LeaveRequestStatus,
  OnDutyRequestStatus,
} from '@/types/hr'
import type {
  OrganisationAccessState,
  OrganisationBillingStatus,
  OrganisationOnboardingStage,
  OrganisationStatus,
} from '@/types/organisation'

type Tone = 'neutral' | 'info' | 'success' | 'warning' | 'danger'

export function getOrganisationStatusTone(status?: OrganisationStatus | null): Tone {
  switch (status) {
    case 'ACTIVE':
      return 'success'
    case 'PAID':
      return 'info'
    case 'SUSPENDED':
      return 'danger'
    case 'PENDING':
    default:
      return 'warning'
  }
}

export function getBillingStatusTone(status?: OrganisationBillingStatus | null): Tone {
  switch (status) {
    case 'PAID':
      return 'success'
    case 'PENDING_PAYMENT':
    default:
      return 'warning'
  }
}

export function getAccessStateTone(status?: OrganisationAccessState | null): Tone {
  switch (status) {
    case 'ACTIVE':
      return 'success'
    case 'SUSPENDED':
      return 'danger'
    case 'PROVISIONING':
    default:
      return 'info'
  }
}

export function getEmployeeStatusTone(status?: EmployeeStatus | null): Tone {
  switch (status) {
    case 'ACTIVE':
      return 'success'
    case 'PENDING':
      return 'warning'
    case 'INVITED':
      return 'info'
    case 'RESIGNED':
    case 'RETIRED':
    case 'TERMINATED':
      return 'danger'
    default:
      return 'neutral'
  }
}

export function getDocumentStatusTone(status?: DocumentStatus | null): Tone {
  switch (status) {
    case 'VERIFIED':
      return 'success'
    case 'REJECTED':
      return 'danger'
    case 'PENDING':
    default:
      return 'warning'
  }
}

export function getDocumentRequestStatusTone(status?: EmployeeDocumentRequestStatus | null): Tone {
  switch (status) {
    case 'VERIFIED':
    case 'WAIVED':
      return 'success'
    case 'SUBMITTED':
      return 'info'
    case 'REJECTED':
      return 'danger'
    case 'REQUESTED':
    default:
      return 'warning'
  }
}

export function getOnboardingStatusTone(status?: EmployeeOnboardingStatus | null): Tone {
  switch (status) {
    case 'COMPLETE':
      return 'success'
    case 'DOCUMENTS_PENDING':
      return 'info'
    case 'BASIC_DETAILS_PENDING':
    case 'NOT_STARTED':
    default:
      return 'warning'
  }
}

export function getApprovalActionTone(status?: ApprovalActionStatus | null): Tone {
  switch (status) {
    case 'APPROVED':
      return 'success'
    case 'REJECTED':
    case 'CANCELLED':
      return 'danger'
    case 'SKIPPED':
      return 'neutral'
    case 'PENDING':
    default:
      return 'warning'
  }
}

export function getLeaveStatusTone(status?: LeaveRequestStatus | OnDutyRequestStatus | null): Tone {
  switch (status) {
    case 'APPROVED':
      return 'success'
    case 'REJECTED':
    case 'CANCELLED':
      return 'danger'
    case 'WITHDRAWN':
      return 'neutral'
    case 'PENDING':
    default:
      return 'warning'
  }
}

export const ORG_ONBOARDING_STEPS: Array<{
  id: OrganisationOnboardingStage
  label: string
  description: string
}> = [
  {
    id: 'ORG_CREATED',
    label: 'Organisation created',
    description: 'Control Tower provisioned the tenant shell.',
  },
  {
    id: 'LICENCES_ASSIGNED',
    label: 'Licences assigned',
    description: 'Purchased seats are available for onboarding.',
  },
  {
    id: 'PAYMENT_CONFIRMED',
    label: 'Payment confirmed',
    description: 'External invoice payment has been acknowledged.',
  },
  {
    id: 'ADMIN_INVITED',
    label: 'Primary admin invited',
    description: 'Organisation administrator has received the invite.',
  },
  {
    id: 'ADMIN_ACTIVATED',
    label: 'Admin activated',
    description: 'The primary admin set a password and accessed the portal.',
  },
  {
    id: 'MASTER_DATA_CONFIGURED',
    label: 'Master data configured',
    description: 'Locations and departments are ready for employee setup.',
  },
  {
    id: 'EMPLOYEES_INVITED',
    label: 'Employees invited',
    description: 'At least one employee has entered the onboarding funnel.',
  },
]
