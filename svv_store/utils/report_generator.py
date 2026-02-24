import csv
import io
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.utils.timezone import now


def generate_csv(data, filename):
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Product Name", "Variant", "Price", "Quantity Sold"])  # customize columns
    for row in data:
        writer.writerow([row['product_name'], row['variant_quantity'], row['price'], row['total_quantity_sold']])

    file_path = f'reports/{filename}.csv'
    default_storage.save(file_path, ContentFile(buffer.getvalue()))
    return file_path


def generate_pdf(data, filename):
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    p.setFont("Helvetica", 12)

    y = 750
    p.drawString(50, y, "Sales Report")
    y -= 25
    for row in data:
        line = f"{row['product_name']} - {row['variant_quantity']} - {row['price']} - {row['total_quantity_sold']}"
        p.drawString(50, y, line)
        y -= 20

    p.showPage()
    p.save()

    file_path = f'reports/{filename}.pdf'
    default_storage.save(file_path, ContentFile(buffer.getvalue()))
    return file_path
