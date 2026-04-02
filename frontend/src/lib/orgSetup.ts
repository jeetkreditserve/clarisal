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

const ORG_SETUP_ALLOWED_PATH_PREFIXES: Record<OrgAdminSetupStep, string[]> = {
  PROFILE: ['/org/profile'],
  ADDRESSES: ['/org/profile'],
  LOCATIONS: ['/org/locations'],
  DEPARTMENTS: ['/org/departments'],
  HOLIDAYS: ['/org/holidays'],
  POLICIES: [
    '/org/leave-cycles',
    '/org/leave-plans',
    '/org/on-duty-policies',
    '/org/approval-workflows',
    '/org/notices',
  ],
  EMPLOYEES: ['/org/employees'],
}

export function normalizeOrgSetupStep(step: string | null | undefined): OrgAdminSetupStep {
  return step && step in ORG_SETUP_ROUTES ? (step as OrgAdminSetupStep) : 'PROFILE'
}

export function isOrgSetupPathAllowed(step: string | null | undefined, pathname: string) {
  const normalizedStep = normalizeOrgSetupStep(step)
  return ORG_SETUP_ALLOWED_PATH_PREFIXES[normalizedStep].some((prefix) => pathname.startsWith(prefix))
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
