import type { OrgAdminSetupState, OrgAdminSetupStep } from '@/types/organisation'

export const ORG_SETUP_ROUTES: Record<OrgAdminSetupStep, string> = {
  PROFILE: '/org/profile',
  ADDRESSES: '/org/profile',
  LOCATIONS: '/org/locations',
  DEPARTMENTS: '/org/departments',
  HOLIDAYS: '/org/holidays',
  POLICIES: '/org/leave-cycles',
  EMPLOYEES: '/org/employees',
}

export function getOrgSetupRoute(step: OrgAdminSetupStep) {
  return ORG_SETUP_ROUTES[step]
}

export function getNextOrgSetupStep(setup: OrgAdminSetupState): OrgAdminSetupStep | null {
  const currentIndex = setup.steps.findIndex((step) => step.key === setup.current_step)
  if (currentIndex === -1 || currentIndex === setup.steps.length - 1) {
    return null
  }
  return setup.steps[currentIndex + 1].key
}

export function getPreviousOrgSetupStep(setup: OrgAdminSetupState): OrgAdminSetupStep | null {
  const currentIndex = setup.steps.findIndex((step) => step.key === setup.current_step)
  if (currentIndex <= 0) {
    return null
  }
  return setup.steps[currentIndex - 1].key
}
