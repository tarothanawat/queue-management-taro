from abc import ABC, abstractmethod

from mypy.state import state

from participant.models import RestaurantParticipant, Participant, BankParticipant
from manager.models import Resource, RestaurantQueue, Queue, BankQueue
from django.shortcuts import get_object_or_404
from django.utils import timezone

class ParticipantHandlerFactory:
    @staticmethod
    def get_handler(queue_id):
        queue = get_object_or_404(Queue, id=queue_id)
        queue_category = queue.category
        if queue_category == 'general':
            return GeneralParticipantHandler()
        elif queue_category == 'restaurant':
            return RestaurantParticipantHandler()
        # elif queue_category == 'hospital':
        #     return HospitalParticipantHandler()
        elif queue_category == 'bank':
            return BankParticipantHandler()
        else:
            return GeneralParticipantHandler()
            # raise ValueError(f"Unknown category: {queue_category}")



class ParticipantHandler(ABC):
    @abstractmethod
    def create_participant(self, data):
        pass

    @abstractmethod
    def get_participant_set(self, queue_id):
        pass

    @abstractmethod
    def get_queue_object(self, queue_id):
        pass


    @abstractmethod
    def assign_to_resource(self, participant):
        pass

    @abstractmethod
    def complete_service(self, participant):
        pass

    @abstractmethod
    def add_context_attributes(self, queue):
        """Returns restaurant-specific attributes for the context."""
        pass

    @abstractmethod
    def get_template_name(self):
        """Return the template name specific to the handler's category."""
        pass

    @abstractmethod
    def get_participant_data(self, participant):
        pass

    @abstractmethod
    def update_participant(self, participant, data):
        pass

    @abstractmethod
    def get_special_column(self):
        pass

    @abstractmethod
    def get_resource_name(self):
        pass

class GeneralParticipantHandler(ParticipantHandler):
    def create_participant(self, data):
        return Participant.objects.create(**data)

    def get_participant_set(self, queue_id):
        return Participant.objects.filter(queue_id=queue_id)

    def get_queue_object(self, queue_id):
        return get_object_or_404(Queue, id=queue_id)

    def assign_to_resource(self, participant):
        pass

    def complete_service(self, participant):
        if participant.state == 'serving':
            if participant.service_started_at:
                wait_time = int((participant.service_started_at - participant.joined_at).total_seconds() / 60)
                participant.waited = wait_time
            participant.state = 'completed'
            participant.service_completed_at = timezone.localtime()
            participant.save()

    def get_template_name(self):
        return 'manager/manage_queue/manage_general.html'

    def add_context_attributes(self, queue):
        pass

    def update_participant(self, participant, data):
        participant.name = data.get('name', participant.name)
        participant.phone = data.get('phone', participant.phone)
        participant.note = data.get('notes', participant.note)
        participant.save()

    def get_participant_data(self, participant):
        return {
            'id': participant.id,
            'name': participant.name,
            'phone': participant.phone,
            'position': participant.position,
            'notes': participant.note,
            'waited': participant.get_wait_time(),
        }
    def get_special_column(self):
        pass

class RestaurantParticipantHandler(ParticipantHandler):
    def create_participant(self, data):
        return RestaurantParticipant.objects.create(**data)

    def get_participant_set(self, queue_id):
        return RestaurantParticipant.objects.filter(queue_id=queue_id).all()

    def get_queue_object(self, queue_id):
        return get_object_or_404(RestaurantQueue, id=queue_id)

    def assign_to_resource(self, participant):
        queue = participant.queue
        resource = queue.get_available_resource(required_capacity=participant.party_size)
        if resource:
            resource.assign_to_participant(participant, capacity=participant.party_size)
        else:
            raise ValueError("No available resources")

    def get_template_name(self):
        return 'manager/manage_queue/manage_restaurant.html'

    def complete_service(self, participant):
        if participant.state == 'serving':
            if participant.service_started_at:
                wait_duration = int((participant.service_started_at - participant.joined_at).total_seconds() / 60)
                participant.waited = wait_duration
            service_duration = int((timezone.localtime() - participant.service_started_at).total_seconds() / 60)
            participant.service_duration = service_duration
            if participant.resource:
                participant.table_served = participant.resource.name
                participant.resource.status = 'empty'
                participant.resource.save()
                participant.resource = None
            participant.state = 'completed'
            participant.service_completed_at = timezone.localtime()
            participant.save()

    def add_context_attributes(self, queue):
        """
        Returns restaurant-specific attributes for the context.
        """
        pass

    def update_participant(self, participant, data):
        participant.name = data.get('name', participant.name)
        participant.phone = data.get('phone', participant.phone)
        participant.party_size = data.get('party_size', participant.party_size)
        participant.note = data.get('notes', participant.note)
        participant.seating_preference = data.get('seating_preference', participant.seating_preference)

        if participant.state == 'completed':
            table_id = data.get('table')
            table = get_object_or_404(Table, id=table_id)
            participant.table_served = table.name
        else:
            table_id = data.get('table')
            if table_id:
                table = get_object_or_404(participant.queue.tables, id=table_id)
                table.assign_to_party(participant)
        participant.save()

    def get_participant_data(self, participant):
        return {
            'id': participant.id,
            'name': participant.name,
            'phone': participant.phone,
            'position': participant.position,
            'notes': participant.note,
            'waited': participant.waited if state=='completed' else participant.get_wait_time(),
            'completed': participant.service_completed_at.strftime('%d %b. %Y %H:%M') if participant.service_completed_at else None,
            'special_1': f"{participant.party_size} people",
            'special_2': participant.seating_preference,
            'service_duration': participant.get_service_duration(),
            'served': participant.service_started_at.strftime(
                '%d %b. %Y %H:%M') if participant.service_started_at else None,
            'resource_served': participant.table_served,
            'resource': participant.resource.name if participant.resource else None,
            'resource_id': participant.resource.id if participant.resource else None,
        }

    def get_special_column(self):
        return 'Party Size', 'Seating Preference'

    def get_resource_name(self):
        return 'Table'

# class HospitalParticipantHandler(BaseParticipantHandler):
#     def create_participant(self, data):
#         return HospitalParticipant.objects.create(**data)
#
#     def assign_to_resource(self, participant):
#         # Logic to assign the participant to a doctor
#         doctor = self.get_available_doctor()
#         if doctor:
#             doctor.assign_patient(participant)
#
#     def get_available_doctor(self):
#         # Implement logic to find an available doctor
#         return Doctor.objects.filter(is_available=True).first()
#
class BankParticipantHandler(ParticipantHandler):
    def create_participant(self, data):
        return BankParticipant.objects.create(**data)

    def get_participant_set(self, queue_id):
        return BankParticipant.objects.filter(queue_id=queue_id)

    def get_queue_object(self, queue_id):
        return get_object_or_404(BankQueue, id=queue_id)

    def assign_to_resource(self, participant):
        queue = participant.queue
        resource = queue.get_available_resource()
        if resource:
            resource.assign_to_participant(participant)
        else:
            raise ValueError("No available resources")

    def complete_service(self, participant):
        if participant.state == 'serving':
            if participant.service_started_at:
                wait_duration = int((participant.service_started_at - participant.joined_at).total_seconds() / 60)
                participant.waited = wait_duration
            service_duration = int((timezone.localtime() - participant.service_started_at).total_seconds() / 60)
            participant.service_duration = service_duration
            if participant.resource:
                participant.counter_served = participant.resource.name
                participant.resource.status = 'empty'
                participant.resource.save()
                participant.resource = None
            participant.state = 'completed'
            participant.service_completed_at = timezone.localtime()
            participant.save()

    def get_template_name(self):
        return 'manager/manage_queue/manage_bank.html'

    def add_context_attributes(self, queue):
        pass

    def update_participant(self, participant, data):
        participant.name = data.get('name', participant.name)
        participant.phone = data.get('phone', participant.phone)
        participant.note = data.get('notes', participant.note)
        participant.save()

    def get_participant_data(self, participant):
        return {
            'id': participant.id,
            'name': participant.name,
            'phone': participant.phone,
            'position': participant.position,
            'special_1': participant.service_type,
            'special_2': None,
            'notes': participant.note,
            'waited': participant.waited if state=='completed' else participant.get_wait_time(),
            'completed': participant.service_completed_at.strftime('%d %b. %Y %H:%M') if participant.service_completed_at else None,
            'service_duration': participant.get_service_duration(),
            'served': participant.service_started_at.strftime(
                '%d %b. %Y %H:%M') if participant.service_started_at else None,
            'resource': participant.resource.name if participant.resource else None,
            'resource_id': participant.resource.id if participant.resource else None,
            'resource_served': participant.counter_served,
        }

    def get_special_column(self):
        return 'Service Type', None

    def get_resource_name(self):
        return 'Counter'