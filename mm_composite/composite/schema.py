import graphene
from graphene.types.generic import GenericScalar  # For dynamic user data
import datetime
import requests


class UserType(graphene.ObjectType):
    id = graphene.Int()
    username = graphene.String()  # Replace with actual user fields
    email = graphene.String()  # Replace with actual user fields


class EnrichedEventType(graphene.ObjectType):
    id = graphene.Int()
    title = graphene.String()
    description = graphene.String()
    datetime = graphene.DateTime()
    location = graphene.String()
    organizer = graphene.Field(UserType)
    participants = graphene.List(UserType)


class Query(graphene.ObjectType):
    enriched_event = graphene.Field(
        EnrichedEventType,
        event_id=graphene.Int(required=True)
    )

    def resolve_enriched_event(self, info, event_id):
        request = info.context.request
        # print(f"headers = {info.context.request.headers}")
        auth_token = request.headers.get('Authorization') if request else None

        headers = {}
        if auth_token:
            headers["Authorization"] = auth_token

        try:
            # Retrieve event from the scheduling service (No auth if unnecessary)
            event_response = requests.get(
                f"http://localhost:8000/events/{event_id}/",
                headers=headers  # Add Authorization only if the token is present
            )
            event_response.raise_for_status()
            event_data = event_response.json()

            # Handle datetime conversion
            datetime_str = event_data.get("datetime")
            if datetime_str:
                try:
                    event_datetime = datetime.datetime.fromisoformat(
                        datetime_str.replace("Z", "+00:00"))
                except ValueError:
                    event_datetime = None
            else:
                event_datetime = None

            # Collect unique user IDs
            user_ids = set()
            if event_data.get('organizer_profile'):
                user_ids.add(event_data['organizer_profile'])
            if event_data.get('participant_ids'):
                user_ids.update(event_data['participant_ids'])

            # Fetch user details
            user_details = {}
            for user_id in user_ids:
                try:
                    user_response = requests.get(
                        f"http://localhost:8001/userinfo/{user_id}/",
                        headers=headers  # Add Authorization only if the token is present
                    )
                    user_response.raise_for_status()
                    user_details[user_id] = user_response.json()
                except requests.RequestException as e:
                    print(f"Failed to fetch user {user_id}: {e}")

            # Enrich event data
            enriched_event = {
                "id": event_data["id"],
                "title": event_data["title"],
                "description": event_data.get("description"),
                "datetime": event_datetime,
                "location": event_data.get("location"),
                "organizer": user_details.get(event_data.get("organizer_profile")),
                "participants": [
                    user_details.get(pid) for pid in event_data.get("participant_ids", [])
                    if pid in user_details
                ],
            }
            return enriched_event

        except requests.RequestException as e:
            print(f"Error retrieving event: {e}")
            return None


schema = graphene.Schema(query=Query)
