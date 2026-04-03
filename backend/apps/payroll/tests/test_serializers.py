from apps.payroll.serializers import (
    CompensationTemplateLineWriteSerializer,
    PayrollTaxSlabWriteSerializer,
)


class TestCompensationTemplateLineWriteSerializer:
    def test_positive_monthly_amount_is_valid(self):
        serializer = CompensationTemplateLineWriteSerializer(
            data={
                'component_code': 'BASIC',
                'name': 'Basic Pay',
                'component_type': 'EARNING',
                'monthly_amount': '50000.00',
            }
        )

        assert serializer.is_valid(), serializer.errors

    def test_zero_monthly_amount_is_valid(self):
        serializer = CompensationTemplateLineWriteSerializer(
            data={
                'component_code': 'BASIC',
                'name': 'Basic Pay',
                'component_type': 'EARNING',
                'monthly_amount': '0.00',
            }
        )

        assert serializer.is_valid(), serializer.errors

    def test_negative_monthly_amount_is_rejected(self):
        serializer = CompensationTemplateLineWriteSerializer(
            data={
                'component_code': 'BASIC',
                'name': 'Basic Pay',
                'component_type': 'EARNING',
                'monthly_amount': '-1000.00',
            }
        )

        assert not serializer.is_valid()
        assert 'monthly_amount' in serializer.errors


class TestPayrollTaxSlabWriteSerializer:
    def test_negative_min_income_is_rejected(self):
        serializer = PayrollTaxSlabWriteSerializer(
            data={
                'min_income': '-1.00',
                'max_income': '300000.00',
                'rate_percent': '5.00',
            }
        )

        assert not serializer.is_valid()
        assert 'min_income' in serializer.errors

    def test_rate_above_100_is_rejected(self):
        serializer = PayrollTaxSlabWriteSerializer(
            data={
                'min_income': '0.00',
                'max_income': '300000.00',
                'rate_percent': '101.00',
            }
        )

        assert not serializer.is_valid()
        assert 'rate_percent' in serializer.errors

    def test_negative_rate_is_rejected(self):
        serializer = PayrollTaxSlabWriteSerializer(
            data={
                'min_income': '0.00',
                'max_income': '300000.00',
                'rate_percent': '-5.00',
            }
        )

        assert not serializer.is_valid()
        assert 'rate_percent' in serializer.errors
