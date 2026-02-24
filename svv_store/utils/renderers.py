from rest_framework.renderers import JSONRenderer
from rest_framework.utils.serializer_helpers import ReturnList, ReturnDict

class CustomRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get("response", None)
        message = "Success" if response and response.status_code in range(200, 300) else "Failed"

        if isinstance(data, (ReturnList, list)):
            response_data = {
                "message": message,
                "data": data,
                "status_code": response.status_code if response else 200
            }
        elif isinstance(data, dict) and "error" in data:
            response_data = {
                "message": "Error",
                "data": data,
                "status_code": response.status_code if response else 400
            }
        else:
            response_data = {
                "message": message,
                "data": data,
                "status_code": response.status_code if response else 200
            }

        return super().render(response_data, accepted_media_type, renderer_context)
