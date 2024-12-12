# Create your views here.

import requests
from rest_framework.views import APIView
from rest_framework.response import Response
# from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from .util import RemoteJWTAuthentication
from datetime import datetime, timedelta


class EventCreateView(APIView):
    authentication_classes = [RemoteJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Forward event data to the scheduling microservice
        event_data = request.data
        print(request.data)
        print("About to request from events microservice:")
        event_response = requests.post(
            "http://localhost:8000/events/",
            json=event_data,
            headers={"Authorization": f"Bearer {request.auth}"}
        )

        # Check if event creation was successful
        if event_response.status_code == 201 or event_response.status_code == 200:
            # Parse the created event data
            created_event = event_response.json()

            # Send emails to participants
            self.send_event_emails(created_event, request.auth)

        print(event_response.text)
        return Response(event_response.json(), status=event_response.status_code)

    def send_event_emails(self, event, auth_token):
        """
        Send email notifications to all participants about the newly created event.

        :param event: Dict containing event details
        :param auth_token: Authentication token for making requests
        """
        # Collect participant IDs
        participant_ids = event.get('participant_ids', [])

        # Fetch details for each participant
        for participant_id in participant_ids:
            try:
                # Fetch participant details
                user_response = requests.get(
                    f"http://localhost:8001/userinfo/{participant_id}/",
                    headers={"Authorization": f"Bearer {auth_token}"}
                )
                user_response.raise_for_status()
                participant = user_response.json()

                # Prepare email data
                email_data = {
                    "subject": f"New Event Invitation: {event.get('title', 'Untitled Event')}",
                    "body": self.construct_event_email_body(event, participant),
                    "recipient_list": participant.get('email'),
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M")
                }

                # Send email
                self.send_email(email_data)

            except requests.RequestException as e:
                print(f"Failed to send email to participant {
                      participant_id}: {e}")

    def construct_event_email_body(self, event, participant):
        """
        Construct a personalized email body for the event invitation.

        :param event: Dict containing event details
        :param participant: Dict containing participant details
        :return: Formatted email body
        """
        return f"""Hi {participant.get('first_name', 'Participant')},

You've been invited to a new event:

Event: {event.get('title', 'Untitled Event')}
Description: {event.get('description', 'No description provided')}
Start Time: {event.get('start_time', 'Not specified')}
Location: {event.get('location', 'Not specified')}

Please check your event details and confirm your availability.

Best regards,
Your Event Management Team"""

    def send_email(self, email_data):
        """
        Send email via the email microservice.

        :param email_data: Dict containing email details
        """
        try:
            email_response = requests.post(
                "http://localhost:8003/send-email",
                json=email_data
            )
            email_response.raise_for_status()
            print(f"Email sent successfully to {email_data['recipient_list']}")
        except requests.RequestException as e:
            print(f"Failed to send email: {e}")


def get_enriched_event(request, event_id):
    """
    Retrieve an event from the scheduling service and enrich
    participant and organizer information with user details.

    :param request: The original request (for authentication)
    :param event_id: ID of the event to retrieve
    :return: Enriched event dictionary
    """
    try:
        # Retrieve the event from scheduling service
        print(f"request.auth: {request.auth}")
        event_response = requests.get(
            f"http://localhost:8000/events/{event_id}/",
            headers={"Authorization": f"Bearer {request.auth}"}
        )
        event_response.raise_for_status()  # Raise an exception for bad responses
        event_data = event_response.json()

        # Collect unique user IDs
        user_ids = set()
        # Add organizer ID
        if event_data.get('organizer_id'):
            user_ids.add(event_data['organizer_id'])

        # Add participant IDs
        if event_data.get('participant_ids'):
            user_ids.update(event_data['participant_ids'])

        # Fetch user details for each unique user ID
        user_details = {}
        for user_id in user_ids:
            try:
                print(f"User id = {user_id}")
                user_response = requests.get(
                    f"http://localhost:8001/userinfo/{user_id}/",
                    headers={"Authorization": f"Bearer {request.auth}"}
                )
                user_response.raise_for_status()
                user_details[user_id] = user_response.json()
            except requests.RequestException as e:
                print(f"Failed to fetch user {user_id}: {e}")

        # Enrich event data with user objects
        if event_data.get('organizer_id'):
            event_data['organizer'] = user_details.get(
                event_data['organizer_id'])

        # Replace participant IDs with user objects
        if event_data.get('participant_ids'):
            event_data['participants'] = [
                user_details.get(pid) for pid in event_data['participant_ids']
                if pid in user_details
            ]

        return event_data

    except requests.RequestException as e:
        print(f"Error retrieving event: {e}")
        return None


class EnrichedEventView(APIView):
    authentication_classes = [RemoteJWTAuthentication]
    permission_classes = [AllowAny]

    def get(self, request, event_id):
        enriched_event = get_enriched_event(request, event_id)

        if enriched_event is None:
            return Response({"detail": "Failed to retrieve event"}, status=500)

        return Response(enriched_event)


def get_enriched_availability(request, availability_id):
    try:
        # Retrieve the availability from scheduling service
        print(f"request.auth: {request.auth}")
        availability_response = requests.get(
            f"http://localhost:8000/availabilities/{availability_id}/",
            headers={"Authorization": f"Bearer {request.auth}"}
        )
        # Raise an exception for bad responses
        availability_response.raise_for_status()
        availability_data = availability_response.json()

        # Collect unique user ID (participant)
        user_ids = set()
        if availability_data.get('participant_id'):
            user_ids.add(availability_data['participant_id'])

        # Fetch user details for the participant
        user_details = {}
        for user_id in user_ids:
            try:
                print(f"User id = {user_id}")
                user_response = requests.get(
                    f"http://localhost:8001/userinfo/{user_id}/",
                    headers={"Authorization": f"Bearer {request.auth}"}
                )
                user_response.raise_for_status()
                user_details[user_id] = user_response.json()
            except requests.RequestException as e:
                print(f"Failed to fetch user {user_id}: {e}")

        # Enrich availability data with user object
        if availability_data.get('participant_id'):
            availability_data['participant'] = user_details.get(
                availability_data['participant_id'])

        # Enrich with event link (URL)
        event_id = availability_data.get('event_id')
        # TODO: Proper HATEOS setup here
        print(availability_data)
        if event_id:
            event_url = f"http://localhost:8002/getevent/{event_id}/"
            # Return event URL instead of full event data
            availability_data['event'] = event_url

        return availability_data

    except requests.RequestException as e:
        print(f"Error retrieving availability: {e}")
        return None


class EnrichedAvailabilityView(APIView):
    authentication_classes = [RemoteJWTAuthentication]
    permission_classes = [AllowAny]

    def get(self, request, availability_id):
        enriched_availability = get_enriched_availability(
            request, availability_id)

        if enriched_availability is None:
            return Response({"detail": "Failed to retrieve availability"}, status=500)

        return Response(enriched_availability)
