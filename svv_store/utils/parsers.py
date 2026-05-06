import json

from rest_framework.parsers import BaseParser
from rest_framework.exceptions import ParseError


class PlainTextJSONParser(BaseParser):
    """
    A DRF parser that accepts requests sent with Content-Type: text/plain
    but whose body is valid JSON.

    Some HTTP clients (Postman without explicit header, mobile SDKs, webhooks)
    send JSON bodies with a 'text/plain' media type. This parser bridges that
    gap so the API does not return 415 Unsupported Media Type.

    Usage — add to a specific view:
        class MyView(APIView):
            parser_classes = [JSONParser, PlainTextJSONParser, FormParser]

    Or add globally in settings.py DEFAULT_PARSER_CLASSES.
    """

    media_type = 'text/plain'

    def parse(self, stream, media_type=None, parser_context=None):
        try:
            raw = stream.read()
            return json.loads(raw)
        except (ValueError, TypeError) as e:
            raise ParseError(f"text/plain body is not valid JSON: {e}")
