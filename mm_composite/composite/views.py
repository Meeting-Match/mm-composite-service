# Create your views here.

import requests
from rest_framework.views import APIView
from rest_framework.response import Response
# from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from .util import RemoteJWTAuthentication
from datetime import datetime, timedelta
import logging

logger = logging.getLogger('composite')

def get_correlation_id(request):
    return getattr(request, 'correlation_id', 'N/A')

class EventCreateView(APIView):
    authentication_classes = [RemoteJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        correlation_id = get_correlation_id(request)
        event_data = request.data
        logger.info('Received event creation request', extra={'correlation_id': correlation_id})

        try:
            logger.debug('Forwarding data to the scheduling microservice', extra={'correlation_id': correlation_id})
            event_response = requests.post(
                'http://localhost:8000/events/', # CHANGE HERE TO THE ACTUAL URL ONCE PUT ON AWS
                json=event_data,
                headers={
                    'Authorization': f'Bearer {request.auth}',
                    'X-Correlation-ID': correlation_id
                }
            )
        except requests.RequestException as e:
            logger.error(f'Error while forwarding event data: {e}', extra={'correlation_id': correlation_id})
            return Response({'detail': 'Failed to forward event data'}, status=500)


        # Check if event creation was successful
        if event_response.status_code == 201 or event_response.status_code == 200:
            # Parse the created event data
            created_event = event_response.json()
            logger.info(f'Event created successfully: {created_event}', extra={'correlation_id': correlation_id})

            # Send emails to participants
            self.send_event_emails(created_event, request.auth, correlation_id)
        else:
            logger.warning(f'Failed to create event: {event_response.text}', extra={'correlation_id': correlation_id})

        return Response(event_response.json(), status=event_response.status_code)

    def send_event_emails(self, event, auth_token, correlation_id):
        """
        Send email notifications to all participants about the newly created event.

        :param event: Dict containing event details
        :param auth_token: Authentication token for making requests
        :param correlation_id: Correlation ID for tracking requests
        """
        # Collect participant IDs
        participant_ids = event.get('participant_ids', [])
        logger.info(f'Sending emails to participants: {participant_ids}', extra={'correlation_id': correlation_id})

        # Fetch details for each participant
        for participant_id in participant_ids:
            try:
                # Fetch participant details
                user_response = requests.get(
                    f"http://localhost:8001/userinfo/{participant_id}/", # CHANGE HERE TO THE ACTUAL URL ONCE PUT ON AWS
                    headers={
                        "Authorization": f"Bearer {auth_token}",
                        "X-Correlation-ID": correlation_id
                    }
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
                logger.error(f'Failed to send email to participant {participant_id}: {e}', extra={'correlation_id': correlation_id})

    def construct_event_email_body(self, event, participant):
        """
        Construct a personalized email body for the event invitation.

        :param event: Dict containing event details
        :param participant: Dict containing participant details
        :return: Formatted email body
        """
        correlation_id = participant.get('correlation_id', 'N/A')
        logger.debug(f'Constructing email body for participant {participant.get('id')}', extra={'correlation_id': correlation_id})
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
        correlation_id = email_data.get('correlation_id', 'N/A')
        logger.info(f'Sending email to {email_data.get("recipient_list")}', extra={'correlation_id': correlation_id})
        try:
            email_response = requests.post(
                "http://localhost:8003/send-email", # CHANGE HERE TO THE ACTUAL URL ONCE PUT ON AWS
                json=email_data,
                headers={"X-Correlation-ID": correlation_id}
            )
            email_response.raise_for_status()
            logger.info(f'Email sent successfully to {email_data.get("recipient_list")}', extra={'correlation_id': correlation_id})
        except requests.RequestException as e:
            logger.error(f'Failed to send email: {e}', extra={'correlation_id': correlation_id})


def get_enriched_event(request, event_id):
    """
    Retrieve an event from the scheduling service and enrich
    participant and organizer information with user details.

    :param request: The original request (for authentication)
    :param event_id: ID of the event to retrieve
    :return: Enriched event dictionary
    """
    correlation_id = get_correlation_id(request)
    logger.info(f'Fetching enriched event with ID {event_id}', extra={'correlation_id': correlation_id})
    try:
        # Retrieve the event from scheduling service
        logger.debug(f'Requesting event data from scheduling service for event ID {event_id}', extra={'correlation_id': correlation_id})
        event_response = requests.get(
            f"http://localhost:8000/events/{event_id}/", # CHANGE URL HERE ADSSSSSSSSSSSSSSSSSSSSSSSSSSSSS
            headers={
                "Authorization": f"Bearer {request.auth}",
                "X-Correlation-ID": correlation_id
            }
        )
        event_response.raise_for_status()  # Raise an exception for bad responses
        event_data = event_response.json()
        logger.info(f'Event data retrieved successfully for event ID {event_id}', extra={'correlation_id': correlation_id})

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
                logger.debug(f'Fetching user data for user ID {user_id}', extra={'correlation_id': correlation_id})
                user_response = requests.get(
                    f"http://localhost:8001/userinfo/{user_id}/", ###################################################
                    headers={
                        "Authorization": f"Bearer {request.auth}",
                        "X-Correlation-ID": correlation_id
                    }
                )
                user_response.raise_for_status()
                user_details[user_id] = user_response.json()
            except requests.RequestException as e:
                logger.error(f'Failed to fetch user data for user ID {user_id}: {e}', extra={'correlation_id': correlation_id})

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

        logger.info(f'Enriched event data for event ID {event_id}', extra={'correlation_id': correlation_id})
        return event_data

    except requests.RequestException as e:
        logger.error(f'Error retrieving event: {e}', extra={'correlation_id': correlation_id}
        return None


class EnrichedEventView(APIView):
    authentication_classes = [RemoteJWTAuthentication]
    permission_classes = [AllowAny]

    def get(self, request, event_id):
        correlation_id = get_correlation_id(request)
        logger.info(f'Fetching enriched event for event_id: {event_id}', extra={'correlation_id': correlation_id})

        enriched_event = get_enriched_event(request, event_id)

        if enriched_event is None:
            logger.error(f'Failed to retrieve event for event_id: {event_id}', extra={'correlation_id': correlation_id})
            return Response({"detail": "Failed to retrieve event"}, status=500)

        logger.info(f'Successfully retrieved enriched event for event_id: {event_id}', extra={'correlation_id': correlation_id})
        return Response(enriched_event)


def get_enriched_availability(request, availability_id):
    correlation_id = get_correlation_id(request)
    try:
        # Retrieve the availability from scheduling service
        logger.info(f'Fetching availability for availability_id: {availability_id}', extra={'correlation_id': correlation_id})
        availability_response = requests.get(
            f"http://localhost:8000/availabilities/{availability_id}/", ########################################################
            headers={
                "Authorization": f"Bearer {request.auth}",
                "X-Correlation-ID": correlation_id
            }
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
                logger.info(f'Fetching user details for user_id: {user_id}', extra={'correlation_id': correlation_id})
                user_response = requests.get(
                    f"http://localhost:8001/userinfo/{user_id}/", #########################################################
                    headers={
                        "Authorization": f"Bearer {request.auth}",
                        "X-Correlation-ID": correlation_id
                    }
                )
                user_response.raise_for_status()
                user_details[user_id] = user_response.json()
            except requests.RequestException as e:
                logger.error(f'Failed to fetch user {user_id}: {e}', extra={'correlation_id': correlation_id})

        # Enrich availability data with user object
        if availability_data.get('participant_id'):
            availability_data['participant'] = user_details.get(
                availability_data['participant_id'])

        # Enrich with event link (URL)
        event_id = availability_data.get('event_id')
        # TODO: Proper HATEOS setup here
        if event_id:
            event_url = f"http://localhost:8002/getevent/{event_id}/" ###############################################
            # Return event URL instead of full event data
            availability_data['event'] = event_url

        logger.info(f'Successfully enriched availability for availability_id: {availability_id}', extra={'correlation_id': correlation_id})
        return availability_data

    except requests.RequestException as e:
        logger.error(f'Error retrieving availability for availability_id: {availability_id}: {e}', extra={'correlation_id': correlation_id})
        return None


class EnrichedAvailabilityView(APIView):
    authentication_classes = [RemoteJWTAuthentication]
    permission_classes = [AllowAny]

    def get(self, request, availability_id):
        correlation_id = get_correlation_id(request)
        logger.info(f'Fetching enriched availability for availability_id: {availability_id}', extra={'correlation_id': correlation_id})

        enriched_availability = get_enriched_availability(
            request, availability_id)

        if enriched_availability is None:
            logger.error(f'Failed to retrieve availability for availability_id: {availability_id}', extra={'correlation_id': correlation_id})
            return Response({"detail": "Failed to retrieve availability"}, status=500)

        logger.info(f'Successfully retrieved enriched availability for availability_id: {availability_id}', extra={'correlation_id': correlation_id})
        return Response(enriched_availability)
