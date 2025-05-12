from rest_framework import viewsets, permissions, status, filters
from rest_framework.decorators import action, api_view, authentication_classes, permission_classes
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from django.utils import timezone
from django.db.models import Q
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user
from django.contrib.auth import get_user_model
from django.utils.functional import SimpleLazyObject
from django.contrib.auth import get_user_model
from apps.authentication.models import User as AuthUser  # Adjust import path
from django.contrib.auth import get_user_model
from apps.authentication.models import User as AuthUser 
from django.core.mail import send_mail
from django.conf import settings
from rest_framework.permissions import AllowAny


from .models import User, Course, Enrollment, Issue, Comment, AuditLog, Notification
from .serializers import (
    UserSerializer, CourseSerializer, EnrollmentSerializer,
    IssueSerializer, CommentSerializer,
    AuditLogSerializer, NotificationSerializer
)
from apps.authentication.custom_auth import DebugAuthentication

@api_view(['GET'])
@authentication_classes([DebugAuthentication, TokenAuthentication, SessionAuthentication])
@permission_classes([permissions.IsAuthenticated])
def debug_auth(request):
    user = request.user
    return Response({
        'username': str(user),
        'is_authenticated': getattr(user, 'is_authenticated', False),
        'user_type': type(user).__name__,
        'has_user_type_attr': hasattr(user, 'user_type'),
        'user_type_value': getattr(user, 'user_type', None),
        'user_id': getattr(user, 'id', None)
    })
class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        user = self.request.user  # Directly access the user from the request
        comment = serializer.save(user=user)

        # Notify relevant users about the new comment
        issue = comment.issue
        recipients = set()

        if issue.student:
            recipients.add(issue.student)
        if issue.assigned_to:
            recipients.add(issue.assigned_to)

        for recipient in recipients:
            if recipient != user:  # Don't notify the person who created the comment
                Notification.objects.create(
                    user=recipient,
                    title="New Comment",
                    message=f"A new comment was added to issue '{issue.title}'.",
                    issue=issue
                )
    def get_queryset(self):
        request_user = self.request.user
        user_type = request_user.user_type
        
        # For students, temporarily return all comments for any issues
        if user_type == 'student':
            print("Returning all comments for student as a temporary fix")
            # Get comments for all issues since they don't have student assignments
            return Comment.objects.all()
        
        # Existing code for lecturer...
        elif user_type == 'lecturer':
            # ...
        
          return Comment.objects.all()
class IsStudentPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'student'


class IsLecturerPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'lecturer'


class IsAdminPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'admin'



class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['username', 'email', 'first_name', 'last_name']
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [permissions.IsAdminUser()]
        return [permissions.IsAuthenticated(), IsAdminPermission()]

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)

class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.all()
    serializer_class = CourseSerializer
    filter_backends = [filters.SearchFilter]
    search_fields = ['course_code', 'course_name']

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]

    @action(detail=False, methods=['get'], permission_classes=[permissions.IsAuthenticated, IsLecturerPermission])
    def my_courses(self, request):
        courses = Course.objects.filter(lecturer=request.user)
        serializer = self.get_serializer(courses, many=True)
        return Response(serializer.data)

User = get_user_model()

class EnrollmentViewSet(viewsets.ModelViewSet):
    queryset = Enrollment.objects.all()
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
         # Adjust import path        
        # Get the authenticated user
        user = self.request.user
        
        # Print debug info
        print(f"Current user: {user}, ID: {user.id}, Type: {type(user)}")
        print(f"Auth User model: {get_user_model()}")
        print(f"App User model: {AuthUser}")
        
        # Get Enrollment model's expected User type
        from apps.issues.models import Enrollment
        related_model = Enrollment._meta.get_field('student').related_model
        print(f"Enrollment.student expects: {related_model}")
        
        # Use the exact model type
        correct_user = related_model.objects.get(id=user.id)
        print(f"Correct user instance: {correct_user}, Type: {type(correct_user)}")
        
        # Save with the correct user instance
        serializer.save(student=correct_user)
    def get_queryset(self):
        user = self.request.user
        User = get_user_model()  # Get the User model
        
        if isinstance(user, SimpleLazyObject):
            user = user._wrapped
        
        # Now the User model is properly imported
        if isinstance(user, str):
            try:
                user = User.objects.get(username=user)
            except User.DoesNotExist:
                return Enrollment.objects.none()
        
        if not hasattr(user, 'user_type'):
            return Enrollment.objects.none()
        
        if user.user_type == 'student':
            return Enrollment.objects.filter(student=user)
        elif user.user_type == 'lecturer':
            return Enrollment.objects.filter(course__lecturer=user)
        elif user.user_type == 'admin':
            return Enrollment.objects.all()
        
        return Enrollment.objects.none()
class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AuditLog.objects.all()
    serializer_class = AuditLogSerializer
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        issue_id = self.request.query_params.get('issue', None)
        if issue_id:
            return AuditLog.objects.filter(issue_id=issue_id)
        
        user = self.request.user
        # Handle string username case
        if isinstance(user, str):
            try:
               
                user = AuthUser.objects.get(username=user)
            except (ImportError, AuthUser.DoesNotExist):
                return AuditLog.objects.none()
        
        # Check for proper user object
        if not hasattr(user, 'user_type'):
            return AuditLog.objects.none()
        
        # Assuming your Issue model has created_by or reported_by field instead of student
        if user.user_type == 'student':
            # Use the correct field name for your Issue model
            # This might be issue__created_by_id, issue__reported_by_id, etc.
            return AuditLog.objects.filter()
        elif user.user_type == 'lecturer':
            return AuditLog.objects.filter(
                Q(issue__course__lecturer_id=user.id) | Q(issue__assigned_to_id=user.id)
            ).distinct()
        
        # For admin users, return all audit logs
        return AuditLog.objects.all()
class IssueViewSet(viewsets.ModelViewSet):
    # queryset = Issue.objects.all()
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = IssueSerializer

    def get_queryset(self):
        user = self.request.user._wrapped

        if isinstance(user, str):
            try:
                user = User.objects.get(username=user)
            except User.DoesNotExist:
                return Issue.objects.none()

        if not isinstance(user, User):
            return Issue.objects.none()

        if user.user_type == 'student':
            return Issue.objects.filter(student=user)
        elif user.user_type == 'lecturer':
            return Issue.objects.all()
        elif user.user_type == 'admin':
            return Issue.objects.all()

        return Issue.objects.none()


   

    def perform_create(self, serializer):
        user = self.request.user._wrapped
        if user.user_type == 'student':
            serializer.save(student=user)
        else:
            serializer.save()

        issue = serializer.instance

        # Notify admins (unchanged)
        admins = User.objects.filter(user_type='admin')
        for admin in admins:
            Notification.objects.create(
                user=admin,
                title="New Issue Created",
                message=f"New issue '{issue.title}' was created",
                issue=issue
            )
            # Optional: email to admin
            if settings.EMAIL_HOST:
                try:
                    send_mail(
                        subject="New Issue Notification",
                        message=f"A new issue titled '{issue.title}' was submitted by {user.get_full_name()} ({user.username}).",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[admin.email],
                        fail_silently=True,
                    )
                except Exception as e:
                    print(f"Email to admin {admin.email} failed: {e}")

        # Notify the student (confirmation)
        Notification.objects.create(
            user=issue.student,
            title="Issue Submitted",
            message=f"Your issue '{issue.title}' has been submitted successfully.",
            issue=issue
        )
        if settings.EMAIL_HOST:
            try:
                send_mail(
                    subject="Issue Submitted",
                    message=f"Hello {issue.student.get_full_name()},\n\nYour issue '{issue.title}' has been successfully submitted.",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[issue.student.email],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Email to student {issue.student.email} failed: {e}")

        # Notify the assigned lecturer (if any)
        if issue.assigned_to and issue.assigned_to.user_type == 'lecturer':
            Notification.objects.create(
                user=issue.assigned_to,
                title="New Issue Assigned",
                message=f"You have been assigned a new issue: '{issue.title}'",
                issue=issue
            )
            if settings.EMAIL_HOST:
                try:
                    send_mail(
                        subject="New Issue Assigned to You",
                        message=f"Hello {issue.assigned_to.get_full_name()},\n\nYou have been assigned to a new issue titled '{issue.title}' submitted by {issue.student.get_full_name()}.",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[issue.assigned_to.email],
                        fail_silently=True,
                    )
                except Exception as e:
                    print(f"Email to lecturer {issue.assigned_to.email} failed: {e}")




        @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
        def assign(self, request, pk=None):
            issue = self.get_object()
            assigned_to_id = request.data.get('assigned_to')

            try:
                assigned_to = User.objects.get(id=assigned_to_id)
                if assigned_to.user_type not in ['lecturer', 'admin']:
                    return Response({"error": "Can only assign to lecturers or admins"}, status=status.HTTP_400_BAD_REQUEST)

                old_assigned = issue.assigned_to
                issue.assigned_to = assigned_to
                issue.save()

                AuditLog.objects.create(
                    issue=issue,
                    user=request.user,
                    action="Issue assigned",
                    old_value=str(old_assigned) if old_assigned else "None",
                    new_value=str(assigned_to)
                )

                Notification.objects.create(
                    user=assigned_to,
                    title="Issue Assigned",
                    message=f"You have been assigned to issue '{issue.title}'",
                    issue=issue
                )

                return Response({"success": "Issue assigned successfully"})
            except User.DoesNotExist:
                return Response({"error": "User not found"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def change_status(self, request, pk=None):
        issue = self.get_object()
        new_status = request.data.get('status')

        if new_status not in [choice[0] for choice in Issue.STATUS_CHOICES]:
            return Response({"error": "Invalid status"}, status=status.HTTP_400_BAD_REQUEST)

        old_status = issue.status
        issue.status = new_status

        if new_status == 'resolved':
            issue.resolved_at = timezone.now()

        issue.save()

        AuditLog.objects.create(
            issue=issue,
            user=request.user,
            action="Status changed",
            old_value=old_status,
            new_value=new_status
        )

        Notification.objects.create(
            user=issue.student,
            title="Issue Status Updated",
            message=f"Your issue '{issue.title}' status has been updated to {issue.get_status_display()}",
            issue=issue
        )

        if settings.EMAIL_HOST:
            try:
                send_mail(
                    subject=f"Issue Status Update: {issue.title}",
                    message=f"Your issue '{issue.title}' status has been updated to {issue.get_status_display()}",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[issue.student.email],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Email sending failed: {e}")

        return Response({"success": "Status updated successfully"})

    @action(detail=True, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def update_grade(self, request, pk=None):
        issue = self.get_object()
        new_grade = request.data.get('new_grade')

        if not new_grade:
            return Response({"error": "New grade is required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            new_grade = float(new_grade)
        except ValueError:
            return Response({"error": "Invalid grade format"}, status=status.HTTP_400_BAD_REQUEST)

        old_grade = issue.current_grade
        issue.current_grade = new_grade
        issue.save()

        if issue.enrollment:
            issue.enrollment.current_grade = new_grade
            issue.enrollment.save()

        AuditLog.objects.create(
            issue=issue,
            user=request.user,
            action="Grade updated",
            old_value=str(old_grade) if old_grade else "None",
            new_value=str(new_grade)
        )

        Notification.objects.create(
            user=issue.student,
            title="Grade Updated",
            message=f"Your grade for {issue.course.course_code} has been updated to {new_grade}",
            issue=issue
        )

        return Response({"success": "Grade updated successfully"})
class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    authentication_classes = []
    permission_classes = [AllowAny]
    def get_queryset(self):
            user = self.request.user
            if user.is_authenticated:
                return Notification.objects.filter(user=user)
            else:
                return Notification.objects.none()
