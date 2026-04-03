from datetime import date, timedelta

from apps.timeoff.serializers import LeaveRequestCreateSerializer


class TestLeaveRequestCreateSerializer:
    def _build_data(self, *, start_date, end_date):
        return {
            'leave_type_id': '11111111-1111-1111-1111-111111111111',
            'start_date': start_date.isoformat(),
            'end_date': end_date.isoformat(),
            'start_session': 'FULL_DAY',
            'end_session': 'FULL_DAY',
            'reason': 'Medical leave',
        }

    def test_same_day_leave_is_valid(self):
        today = date.today()
        serializer = LeaveRequestCreateSerializer(
            data=self._build_data(start_date=today, end_date=today)
        )

        assert serializer.is_valid(), serializer.errors

    def test_multi_day_leave_is_valid(self):
        today = date.today()
        serializer = LeaveRequestCreateSerializer(
            data=self._build_data(start_date=today, end_date=today + timedelta(days=3))
        )

        assert serializer.is_valid(), serializer.errors

    def test_end_date_before_start_date_is_rejected(self):
        today = date.today()
        serializer = LeaveRequestCreateSerializer(
            data=self._build_data(start_date=today + timedelta(days=2), end_date=today)
        )

        assert not serializer.is_valid()
        assert 'end_date' in serializer.errors
