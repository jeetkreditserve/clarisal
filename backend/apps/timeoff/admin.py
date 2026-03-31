from django.contrib import admin

from .models import (
    Holiday,
    HolidayCalendar,
    HolidayCalendarLocation,
    LeaveBalance,
    LeaveBalanceLedgerEntry,
    LeaveCycle,
    LeavePlan,
    LeavePlanEmployeeAssignment,
    LeavePlanRule,
    LeaveRequest,
    LeaveType,
    OnDutyPolicy,
    OnDutyRequest,
)


admin.site.register(HolidayCalendar)
admin.site.register(HolidayCalendarLocation)
admin.site.register(Holiday)
admin.site.register(LeaveCycle)
admin.site.register(LeavePlan)
admin.site.register(LeavePlanRule)
admin.site.register(LeavePlanEmployeeAssignment)
admin.site.register(LeaveType)
admin.site.register(LeaveBalance)
admin.site.register(LeaveBalanceLedgerEntry)
admin.site.register(LeaveRequest)
admin.site.register(OnDutyPolicy)
admin.site.register(OnDutyRequest)

