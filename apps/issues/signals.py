from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Issue, Comment, Notification, AuditLog

User = get_user_model()

@receiver(post_save, sender=Issue)
def issue_created_notification(sender, instance, created, **kwargs):
    """
    Signal to create in-app notifications when a new issue is created
    """
    if created:
        # Create notification for the lecturer
        if instance.course.lecturer:
            Notification.objects.create(
                user=instance.course.lecturer,
                title=f"New Issue: {instance.title}",
                message=f"A new issue has been created for your course {instance.course.course_code} by {instance.student.get_full_name()}.",
                issue=instance
            )
        
        # Create notification for admin users
        admin_users = User.objects.filter(is_staff=True)
        for admin in admin_users:
            Notification.objects.create(
                user=admin,
                title=f"New Issue: {instance.title}",
                message=f"A new issue has been created for course {instance.course.course_code} by {instance.student.get_full_name()}.",
                issue=instance
            )

@receiver(post_save, sender=Comment)
def comment_created_notification(sender, instance, created, **kwargs):
    """
    Signal to create in-app notifications when a comment is created
    """
    if created:
        issue = instance.issue
        
        # For the student (if comment is from lecturer or admin)
        if instance.user != issue.student:
            Notification.objects.create(
                user=issue.student,
                title=f"New Comment on Issue: {issue.title}",
                message=f"A new comment has been added to your issue by {instance.user.get_full_name()}.",
                issue=issue
            )
        
        # For the lecturer (if comment is from student or admin)
        if issue.course.lecturer and instance.user != issue.course.lecturer:
            Notification.objects.create(
                user=issue.course.lecturer,
                title=f"New Comment on Issue: {issue.title}",
                message=f"A new comment has been added to an issue for your course {issue.course.course_code} by {instance.user.get_full_name()}.",
                issue=issue
            )
        
        # For admin users (if comment is not from an admin)
        if not instance.user.is_staff:
            admin_users = User.objects.filter(is_staff=True)
            for admin in admin_users:
                if admin != instance.user:  # Don't notify admin about their own comment
                    Notification.objects.create(
                        user=admin,
                        title=f"New Comment on Issue: {issue.title}",
                        message=f"A new comment has been added to an issue for course {issue.course.course_code} by {instance.user.get_full_name()}.",
                        issue=issue
                    )

@receiver(pre_save, sender=Issue)
def track_issue_changes(sender, instance, **kwargs):
    """
    Signal to track changes to issues and notify relevant parties
    """
    if instance.pk:  # If this is an update, not a new instance
        try:
            old_instance = Issue.objects.get(pk=instance.pk)
            
            # Check for status change
            if old_instance.status != instance.status:
                # Create notification for the student
                Notification.objects.create(
                    user=instance.student,
                    title=f"Issue Status Changed: {instance.title}",
                    message=f"Your issue status has been updated from '{old_instance.get_status_display()}' to '{instance.get_status_display()}'.",
                    issue=instance
                )
                
                # Create notification for lecturer if not the one who made the change
                if instance.course.lecturer and (not instance.assigned_to or instance.assigned_to != instance.course.lecturer):
                    Notification.objects.create(
                        user=instance.course.lecturer,
                        title=f"Issue Status Changed: {instance.title}",
                        message=f"Issue status has been updated from '{old_instance.get_status_display()}' to '{instance.get_status_display()}'.",
                        issue=instance
                    )
                
                # Audit log is created in the view
                
            # Check for grade change
            if old_instance.current_grade != instance.current_grade and instance.current_grade is not None:
                # Notify student of grade change
                Notification.objects.create(
                    user=instance.student,
                    title=f"Grade Updated: {instance.title}",
                    message=f"Your issue has been graded. New grade: {instance.current_grade}",
                    issue=instance
                )
                
                # Create audit log if not already created in the view
                # This serves as a backup in case grade is changed outside the API
                AuditLog.objects.create(
                    issue=instance,
                    user=instance.assigned_to if instance.assigned_to else instance.course.lecturer,
                    action="Grade updated (auto-tracked)",
                    old_value=str(old_instance.current_grade) if old_instance.current_grade else "None",
                    new_value=str(instance.current_grade)
                )
                
            # Check for priority change
            if old_instance.priority != instance.priority:
                # Notify involved parties
                if instance.assigned_to:
                    Notification.objects.create(
                        user=instance.assigned_to,
                        title=f"Issue Priority Changed: {instance.title}",
                        message=f"Issue priority has been updated from '{old_instance.get_priority_display()}' to '{instance.get_priority_display()}'.",
                        issue=instance
                    )
                    
                # Create audit log
                AuditLog.objects.create(
                    issue=instance,
                    user=instance.assigned_to if instance.assigned_to else instance.course.lecturer,
                    action="Priority changed (auto-tracked)",
                    old_value=old_instance.get_priority_display(),
                    new_value=instance.get_priority_display()
                )
                
            # Check for assigned_to change
            if old_instance.assigned_to != instance.assigned_to:
                # Notify new assignee
                if instance.assigned_to:
                    Notification.objects.create(
                        user=instance.assigned_to,
                        title=f"Issue Assigned to You: {instance.title}",
                        message=f"You have been assigned to handle this issue for course {instance.course.course_code}.",
                        issue=instance
                    )
                
                # Create audit log
                AuditLog.objects.create(
                    issue=instance,
                    user=instance.assigned_to if instance.assigned_to else instance.course.lecturer,
                    action="Assignment changed (auto-tracked)",
                    old_value=str(old_instance.assigned_to) if old_instance.assigned_to else "None",
                    new_value=str(instance.assigned_to) if instance.assigned_to else "None"
                )
                
        except Issue.DoesNotExist:
            # This is a new instance, so no need to check for changes
            pass