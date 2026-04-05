from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


class EmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    username_field = User.USERNAME_FIELD

    def validate(self, attrs):
        credentials = {
            self.username_field: attrs.get(self.username_field),
            'password': attrs.get('password'),
        }
        user = authenticate(request=self.context.get('request'), **credentials)
        if user is None or not user.is_active:
            raise serializers.ValidationError('Invalid email or password.')
        attrs[self.username_field] = getattr(user, self.username_field)
        return super().validate(attrs)
