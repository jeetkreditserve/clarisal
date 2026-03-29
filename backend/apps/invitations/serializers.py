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
    password = serializers.CharField(min_length=8)
    confirm_password = serializers.CharField()

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({'confirm_password': 'Passwords do not match.'})
        return data
