import uuid
import logging

logger = logging.getLogger('composite')

class CorrelationIdMiddleware:
    """
    Middleware to generate and propagate Correlation IDs for incoming requests.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if Correlation ID exists in the request headers
        correlation_id = request.headers.get('X-Correlation-ID', str(uuid.uuid4()))
        request.correlation_id = correlation_id

        # Log the incoming request with the Correlation ID
        logger.info(f"Incoming request: {request.method} {request.path}",
                    extra={'correlation_id': correlation_id})

        # Process the request
        response = self.get_response(request)

        # Add Correlation ID to the response headers
        response['X-Correlation-ID'] = correlation_id

        # Log the response with Correlation ID
        logger.info(f"Outgoing response: {response.status_code} {request.path}",
                    extra={'correlation_id': correlation_id})

        return response