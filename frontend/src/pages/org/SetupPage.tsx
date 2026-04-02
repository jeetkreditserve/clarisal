import { Navigate } from 'react-router-dom'

import { LoadingScreen } from '@/components/ui/LoadingScreen'
import { useOrgSetup } from '@/hooks/useOrgAdmin'
import { getOrgSetupRoute } from '@/lib/orgSetup'

export function OrgSetupPage() {
  const { data: setup, isLoading } = useOrgSetup()

  if (isLoading || !setup) {
    return <LoadingScreen />
  }

  if (!setup.required) {
    return <Navigate to="/org/dashboard" replace />
  }

  return <Navigate to={getOrgSetupRoute(setup.current_step)} replace />
}
