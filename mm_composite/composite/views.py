# Create your views here.

import requests
from rest_framework.views import APIView
from rest_framework.response import Response
# from rest_framework.authentication import BaseAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from .util import RemoteJWTAuthentication


class EventCreateView(APIView):
    authentication_classes = [RemoteJWTAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # At this point, the token is already validated by DRF
        # user = request.user  # DRF automatically provides the authenticated user
        print(f"request.auth: {request.auth}")

        # Forward event data to the scheduling microservice
        event_data = request.data
        print(request.data)
        event_data["organizer"] = 3  # Attach user ID to the event
        print("About to request from events microservice:")
        event_response = requests.post(
            "http://localhost:8000/events/",
            json=event_data,
            headers={"Authorization": f"Bearer {request.auth}"}
        )

        print(event_response.text)
        return Response(event_response.json(), status=event_response.status_code)
