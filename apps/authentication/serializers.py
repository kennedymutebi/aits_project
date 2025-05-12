from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from .models import User, Student, Lecturer
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.auth import get_user_model


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    user_type = serializers.CharField(required=True)  # Add user_type to the serializer
    department = serializers.CharField(required=True) 
    profile_picture = serializers.ImageField(required=False)
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'first_name',
                 'last_name', 'user_type', 'phone_number', 'department','profile_picture']
        
    def create(self, validated_data):
        # Use create_user instead of create
        return User.objects.create_user(**validated_data)
# serializers.py
class AdminRegistrationSerializer(serializers.ModelSerializer):
    user = UserSerializer()

    class Meta:
        model = User
        fields = ['user']

    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user_data['user_type'] = 'admin'  # Ensure user is created as admin
        user_serializer = UserSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()
        return user


class StudentRegistrationSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    
    class Meta:
        model = Student
        fields = ['user', 'student_id', 'program', 'year_of_study']
        
    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user_data['user_type'] = 'student'
        # Use create_user through the UserSerializer
        user_serializer = UserSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()
        student = Student.objects.create(user=user, **validated_data)
        return student

class LecturerRegistrationSerializer(serializers.ModelSerializer):
    user = UserSerializer()
    
    class Meta:
        model = Lecturer
        fields = ['user', 'staff_id']
        
    def create(self, validated_data):
        user_data = validated_data.pop('user')
        user_data['user_type'] = 'lecturer'
        # Use create_user through the UserSerializer
        user_serializer = UserSerializer(data=user_data)
        user_serializer.is_valid(raise_exception=True)
        user = user_serializer.save()
        lecturer = Lecturer.objects.create(user=user, **validated_data)
        return lecturer


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True)

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError('No user is registered with this email.')
        return value

# serializers.py
User = get_user_model()

class SetNewPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField()
    token = serializers.CharField()
    new_password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email')
        token = attrs.get('token')
        password = attrs.get('new_password')

        user = User.objects.get(email=email)
        token_generator = PasswordResetTokenGenerator()

        if not token_generator.check_token(user, token):
            raise serializers.ValidationError('Invalid or expired reset token.')

        user.set_password(password)
        user.save()
        return attrs

