from rest_framework.response import Response
from utils.report_generator import generate_csv, generate_pdf
from utils.signed_url import get_signed_url
import os
from django.conf import settings
from django.http import FileResponse, Http404
from django.utils.timezone import now
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from rest_framework.views import APIView

class SalesReportExportView(APIView):
    def get(self, request):
        # Example dummy data for the report (replace with real data fetching logic)
        data = [
            {
                "product_name": "Bendi H",
                "variant_quantity": "1.00 kg",
                "price": "200.00",
                "total_quantity_sold": 6
            }
        ]

        # Generate timestamp for unique report filenames
        timestamp = now().strftime("%Y%m%d%H%M%S")

        # Generate report files
        csv_file_path = generate_csv(data, f"sales_report_{timestamp}")
        pdf_file_path = generate_pdf(data, f"sales_report_{timestamp}")

        # Generate signed URLs for the generated files
        csv_url = get_signed_url(csv_file_path,request)
        pdf_url = get_signed_url(pdf_file_path,request)

        # Return response with signed URLs
        return Response({
            "message": "Reports generated successfully",
            "data": {
                "csv_report_url": csv_url,
                "pdf_report_url": pdf_url
            },
            "status_code": 200
        })

class SecureFileDownloadView(APIView):
    def get(self, request):
        signer = TimestampSigner()
        signed_file_path = request.GET.get("file")
        expires = request.GET.get("expires")

        if not signed_file_path or not expires:
            raise Http404("Invalid download request.")

        # Check expiration
        try:
            if float(expires) < now().timestamp():
                raise Http404("URL has expired.")
        except ValueError:
            raise Http404("Invalid expiry timestamp.")

        # Unsigned file path (verify signature)
        try:
            file_path = signer.unsign(signed_file_path)
        except (BadSignature, SignatureExpired):
            raise Http404("Invalid or expired signature.")

        full_path = os.path.join(settings.MEDIA_ROOT, file_path)
        if not os.path.exists(full_path):
            raise Http404("File not found.")

        return FileResponse(open(full_path, 'rb'), as_attachment=True)
