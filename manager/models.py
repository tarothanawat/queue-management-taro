import math
import string
import random

from django.db.models import ManyToManyField
from django.utils import timezone
from django.db import models
from django.templatetags.static import static
from django.contrib.auth.models import User


class Queue(models.Model):
    """Represents a queue created by a user."""
    STATUS_CHOICES = [
        ('normal', 'Normal'),
        ('busy', 'Busy'),
        ('full', 'Full'),
    ]
    CATEGORY_CHOICES = [
        ('restaurant', 'Restaurant'),
        ('general', 'General'),
        ('hospital', 'Hospital'),
        ('bank', 'Bank'),
        ('service center', 'Service center')
    ]

    name = models.CharField(max_length=50)
    description = models.TextField(max_length=100)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    authorized_user = models.ManyToManyField(User, related_name='queues', blank=True)
    open_time = models.DateTimeField(null=True, blank=True)
    close_time = models.DateTimeField(null=True, blank=True)
    estimated_wait_time_per_turn = models.PositiveIntegerField(default=0)
    average_service_duration = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(default=timezone.localtime)
    is_closed = models.BooleanField(default=False)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='normal')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    logo = models.ImageField(upload_to='queue_logos/', blank=True, null=True)
    completed_participants_count = models.PositiveIntegerField(default=0)

    def has_resources(self):
        return self.category != 'general'

    def get_resources(self):
        if self.has_resources():
            return self.resource_set.all()
        return None

    def update_estimated_wait_time_per_turn(self, time_taken: int) -> None:
        """Update the estimated wait time per turn based on the time taken for a turn."""
        total_time = (self.estimated_wait_time_per_turn * self.completed_participants_count) + time_taken
        self.completed_participants_count += 1
        self.estimated_wait_time_per_turn = math.ceil(total_time / self.completed_participants_count)
        self.save()

    def calculate_average_service_duration(self, serve_time: int):
        """Update the average serve duration based on recent serve time."""
        if self.completed_participants_count > 0:
            total_serve_time = (self.average_service_duration * self.completed_participants_count) + serve_time
            self.completed_participants_count += 1
            self.average_service_duration = math.ceil(total_serve_time / self.completed_participants_count)
        else:
            self.average_service_duration = serve_time
            self.completed_participants_count += 1
        self.save()

    def get_participants(self) -> models.QuerySet:
        """Return a queryset of all participants in this queue."""
        return self.participant_set.all()

    def get_number_of_participants(self) -> int:
        """Return the count of all participants in this queue."""
        return self.participant_set.count()

    def get_participants_today(self) -> int:
        """Get the total number of participants added to the queue today."""
        today = timezone.now().date()
        return self.participant_set.filter(joined_at__date=today).count()

    def get_logo_url(self):
        """Get a logo URL for the queue, or return a default logo based on category."""
        if self.logo:
            return self.logo.url
        default_logos = {
            'restaurant': static('queue_manager/images/restaurant_default_logo.png'),
            'bank': static('queue_manager/images/bank_default_logo.jpg'),
            'general': static('queue_manager/images/general_default_logo.png'),
            'hospital': static('queue_manager/images/hospital_default_logo.jpg'),
            'service center': static('queue_manager/images/service_center_default_logo.png')
        }
        return default_logos.get(self.category, static('queue_manager/images/default_logo.png'))

    def edit(self, name: str = None, description: str = None, is_closed: bool = None, status: str = None) -> None:
        """Edit the queue's name, description, or closed status."""
        if name:
            if not (1 <= len(name) <= 255):
                raise ValueError("The name must be between 1 and 255 characters.")
            self.name = name
        if description is not None:
            self.description = description
        if is_closed is not None:
            self.is_closed = is_closed
        if status in dict(self.STATUS_CHOICES):
            self.status = status
        self.save()

    def get_available_resource(self, required_capacity=1):
        """
        Fetch an available resource for the specified queue.
        It finds a resource with enough capacity that is currently empty.
        """
        print(self.resource_set)
        return self.resource_set.filter(
            status='empty',
            capacity__gte=required_capacity
        ).first()

    def __str__(self) -> str:
        """Return a string representation of the queue."""
        return self.name


class Resource(models.Model):
    TABLE_STATUS = [
        ('empty', 'Empty'),
        ('busy', 'Busy'),
        ('unavailable', 'Unavailable'),
    ]

    name = models.CharField(max_length=50, unique=True)
    capacity = models.PositiveIntegerField(default=1)
    status = models.CharField(choices=TABLE_STATUS, max_length=15, default='empty')
    queue = models.ForeignKey(Queue, on_delete=models.CASCADE, blank=True, null=True)
    assigned_to = models.ForeignKey('participant.Participant', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='resource_assignment')


    def assign_to_participant(self, participant, capacity=1) -> None:
        """
        Assigns this resource to the given participant if it is available
        and the capacity matches the participant's needs.
        """
        if self.status != 'empty':
            raise ValueError("This resource is not available.")
        if self.capacity < capacity:
            raise ValueError("This resource cannot accommodate the party size.")

        self.status = 'busy'
        self.assigned_to = participant
        self.save()
        participant.resource = self
        participant.save()

    def free(self) -> None:
        """
        Frees the resource, making it available for new assignments.
        """
        if self.status == 'busy' and self.assigned_to:
            self.status = 'empty'
            self.assigned_to = None
            self.save()

    def is_assigned(self) -> bool:
        """
        Checks if this resource is currently assigned to a participant.
        """
        return self.assigned_to is not None

    def change_assignment(self, new_participant) -> None:
        """
        Reassigns the resource to a new participant if it is available or
        belongs to the same queue as the current assignment.
        """
        if self.is_assigned():
            if self.assigned_to.queue != new_participant.queue:
                raise ValueError("The new participant must be in the same queue.")
            self.free()
        self.assign_to_participant(new_participant)

    def __str__(self):
        """Return a string representation of the table."""
        return f"{self.name} (Status: {self.status}, Capacity: {self.capacity})"


class RestaurantQueue(Queue):
    has_outdoor = models.BooleanField(default=False)

class BankQueue(Queue):
    """Represents a queue specifically for bank services."""

    def __str__(self):
        return f"Bank Queue: {self.name}"

class HospitalQueue(Queue):
    doctors = models,ManyToManyField(Resource)


class UserProfile(models.Model):
    """Represents a user profile in the system."""
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_no = models.CharField(max_length=15)

    def __str__(self) -> str:
        """Return a string representation of the user profile."""
        return self.user.username