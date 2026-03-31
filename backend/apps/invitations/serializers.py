from rest_framework import serializers


class InviteOrgAdminSerializer(serializers.Serializer):
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=100)
    last_name = serializers.CharField(max_length=100)


class ValidateInviteResponseSerializer(serializers.Serializer):
    email = serializers.EmailField()
    role = serializers.CharField()
    organisation_name = serializers.CharField(allow_null=True)


class AcceptInviteSerializer(serializers.Serializer):
    token = serializers.CharField()
    password = serializers.CharField(min_length=8, required=False, allow_blank=True, default='')
    confirm_password = serializers.CharField(required=False, allow_blank=True, default='')

    def validate(self, data):
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')
        if password or confirm_password:
            if password != confirm_password:
                raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        elif 'confirm_password' in data and password != confirm_password:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        return data
