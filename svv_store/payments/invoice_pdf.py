import io
from decimal import Decimal
from html import escape

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Flowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


GREEN = colors.HexColor("#2f8f2b")
LEAF = colors.HexColor("#83c51a")
ORANGE = colors.HexColor("#ff7a16")
TEXT = colors.HexColor("#243024")
MUTED = colors.HexColor("#66736a")
LINE = colors.HexColor("#dfe7df")
SOFT_GREEN = colors.HexColor("#eef8ec")
SELLER_INFO = [
    "Vegga Fresh",
    "H No 13-6-448/1, Sai Nagar Colony, Behind Vegetable Market, Guddimalkapur, Hyderabad, 500028",
]


class VeggaFreshLogo(Flowable):
    def __init__(self, width=56 * mm, height=24 * mm):
        super().__init__()
        self.width = width
        self.height = height

    def draw(self):
        c = self.canv
        c.saveState()

        c.setFillColor(GREEN)
        c.setFont("Helvetica-BoldOblique", 46)
        c.drawString(0, 9, "V")

        c.setFillColor(ORANGE)
        c.setFont("Helvetica-BoldOblique", 43)
        c.drawString(26, 9, "F")

        c.setFillColor(LEAF)
        leaf = c.beginPath()
        leaf.moveTo(31, 50)
        leaf.curveTo(48, 67, 76, 52, 82, 70)
        leaf.curveTo(78, 48, 58, 37, 36, 40)
        leaf.curveTo(42, 48, 50, 53, 65, 57)
        leaf.curveTo(52, 57, 42, 54, 31, 50)
        c.drawPath(leaf, fill=1, stroke=0)

        c.setStrokeColor(ORANGE)
        c.setLineWidth(4)
        swoosh = c.beginPath()
        swoosh.moveTo(1, 5)
        swoosh.curveTo(30, 25, 78, 0, 107, 24)
        c.drawPath(swoosh, fill=0, stroke=1)

        c.restoreState()


def _money(value):
    value = Decimal(value or 0)
    return f"INR {value:.2f}"


def _p(text, style):
    return Paragraph(escape(str(text or "")), style)


def _address_lines(address, user=None):
    if not address:
        return ["Address not available"]

    lines = [
        address.full_name,
        address.mobile,
        address.address_line1,
        address.address_line2,
        address.landmark,
        f"{address.city}, {address.state} - {address.pincode}",
        address.country,
    ]
    if user and user.company_name:
        lines.append(f"Company Name: {user.company_name}")
    if user and user.gst_number:
        lines.append(f"GST Number: {user.gst_number}")
    return [str(line) for line in lines if line]


def _payment_reference(payment):
    if payment.payment_gateway == "razorpay":
        return payment.razorpay_payment_id or payment.razorpay_order_id or "-"
    if payment.payment_gateway == "phonepe":
        return payment.phonepe_transaction_id or "-"
    return payment.payment_id


def _charge_rows(order, styles):
    rows = [[_p("Subtotal", styles["Label"]), _p(_money(order.total_amount), styles["RightValue"])]]

    if Decimal(order.taxes or 0) > 0:
        rows.append([_p("Taxes", styles["Label"]), _p(_money(order.taxes), styles["RightValue"])])
    else:
        rows.append([_p("GST (Included in item price, 0%)", styles["Label"]), _p(_money(0), styles["RightValue"])])
    if Decimal(order.handling_charges or 0) > 0:
        rows.append([_p("Handling Charges", styles["Label"]), _p(_money(order.handling_charges), styles["RightValue"])])
    if Decimal(order.delivery_charges or 0) > 0:
        rows.append([_p("Delivery Charges", styles["Label"]), _p(_money(order.delivery_charges), styles["RightValue"])])

    rows.append([Paragraph("<b>Grand Total</b>", styles["Value"]), Paragraph(f"<b>{_money(order.final_amount)}</b>", styles["RightValue"])])
    return rows


def build_invoice_pdf(order, payment):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=16 * mm,
        bottomMargin=16 * mm,
        title=f"Vegga Fresh Invoice {order.order_id}",
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle("InvoiceTitle", parent=styles["Title"], fontSize=20, leading=24, textColor=TEXT))
    styles.add(ParagraphStyle("SmallMuted", parent=styles["Normal"], fontSize=8, leading=11, textColor=MUTED))
    styles.add(ParagraphStyle("Label", parent=styles["Normal"], fontSize=8, leading=11, textColor=MUTED))
    styles.add(ParagraphStyle("Value", parent=styles["Normal"], fontSize=10, leading=13, textColor=TEXT))
    styles.add(ParagraphStyle("RightValue", parent=styles["Value"], alignment=TA_RIGHT))
    styles.add(ParagraphStyle("TableHead", parent=styles["Normal"], fontSize=8, leading=10, textColor=colors.white))
    styles.add(ParagraphStyle("TableCell", parent=styles["Normal"], fontSize=8.5, leading=11, textColor=TEXT))

    story = []

    header = Table(
        [
            [
                VeggaFreshLogo(),
                [
                    Paragraph("TAX INVOICE", styles["InvoiceTitle"]),
                    Paragraph("Fresh vegetables, fruits and daily essentials", styles["SmallMuted"]),
                ],
            ]
        ],
        colWidths=[62 * mm, 95 * mm],
    )
    header.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(header)

    invoice_meta = Table(
        [
            [_p("Invoice No", styles["Label"]), _p(f"VF-{order.order_id}", styles["RightValue"])],
            [_p("Order ID", styles["Label"]), _p(order.order_id, styles["RightValue"])],
            [_p("Invoice Date", styles["Label"]), _p(timezone.localtime(timezone.now()).strftime("%d %b %Y"), styles["RightValue"])],
            [_p("Order Date", styles["Label"]), _p(timezone.localtime(order.created_at).strftime("%d %b %Y, %I:%M %p"), styles["RightValue"])],
        ],
        colWidths=[80 * mm, 77 * mm],
    )
    invoice_meta.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), SOFT_GREEN),
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(invoice_meta)
    story.append(Spacer(1, 8 * mm))

    customer = [
        Paragraph("<b>Bill / Ship To</b>", styles["Value"]),
        *[_p(line, styles["TableCell"]) for line in _address_lines(order.address, order.user)],
    ]
    seller = [
        Paragraph("<b>Seller</b>", styles["Value"]),
        *[_p(line, styles["TableCell"]) for line in SELLER_INFO],
    ]
    payment_box = [
        Paragraph("<b>Payment Details</b>", styles["Value"]),
        _p(f"Method: {order.payment_method.upper()}", styles["TableCell"]),
        _p(f"Gateway: {payment.payment_gateway.upper()}", styles["TableCell"]),
        _p(f"Status: {payment.status}", styles["TableCell"]),
        _p(f"Reference: {_payment_reference(payment)}", styles["TableCell"]),
    ]
    details = Table([[customer, seller, payment_box]], colWidths=[52 * mm, 58 * mm, 47 * mm])
    details.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.4, LINE),
        ("BACKGROUND", (0, 0), (0, 0), colors.white),
        ("BACKGROUND", (1, 0), (1, 0), SOFT_GREEN),
        ("BACKGROUND", (2, 0), (2, 0), colors.HexColor("#fff7ef")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 9),
        ("RIGHTPADDING", (0, 0), (-1, -1), 9),
        ("TOPPADDING", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 9),
    ]))
    story.append(details)
    story.append(Spacer(1, 8 * mm))

    item_rows = [[
        Paragraph("Item", styles["TableHead"]),
        Paragraph("Variant", styles["TableHead"]),
        Paragraph("Qty", styles["TableHead"]),
        Paragraph("Rate", styles["TableHead"]),
        Paragraph("Amount", styles["TableHead"]),
    ]]

    for item in order.items.all():
        variant = item.product_variant
        product = variant.product
        line_total = Decimal(item.price or 0) * Decimal(item.quantity or 0)
        item_rows.append([
            _p(product.name, styles["TableCell"]),
            _p(f"{variant.quantity:g} {variant.unit}", styles["TableCell"]),
            _p(item.quantity, styles["TableCell"]),
            _p(_money(item.price), styles["TableCell"]),
            _p(_money(line_total), styles["TableCell"]),
        ])

    items_table = Table(item_rows, colWidths=[58 * mm, 30 * mm, 17 * mm, 26 * mm, 26 * mm], repeatRows=1)
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), GREEN),
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, LINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("LEFTPADDING", (0, 0), (-1, -1), 7),
        ("RIGHTPADDING", (0, 0), (-1, -1), 7),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 7 * mm))

    totals = Table(
        _charge_rows(order, styles),
        colWidths=[100 * mm, 57 * mm],
        hAlign="RIGHT",
    )
    totals.setStyle(TableStyle([
        ("BOX", (0, 0), (-1, -1), 0.7, LINE),
        ("INNERGRID", (0, 0), (-1, -1), 0.35, LINE),
        ("BACKGROUND", (0, -1), (-1, -1), SOFT_GREEN),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(totals)
    story.append(Spacer(1, 8 * mm))
    story.append(Paragraph("Note: GST is already included in the listed item prices. This invoice reflects a separate GST line of 0%.", styles["SmallMuted"]))
    story.append(Spacer(1, 2 * mm))
    story.append(Paragraph("Thank you for shopping with Vegga Fresh.", styles["Value"]))
    story.append(Paragraph("For support, contact support@veggafresh.com", styles["SmallMuted"]))
    story.append(Paragraph("This is a system generated invoice.", styles["SmallMuted"]))

    def footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(LINE)
        canvas.line(18 * mm, 13 * mm, 192 * mm, 13 * mm)
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(18 * mm, 8 * mm, "Vegga Fresh")
        canvas.drawRightString(192 * mm, 8 * mm, f"Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    buffer.seek(0)
    return buffer.getvalue()
