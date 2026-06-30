from datetime import timedelta

from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from address.models import Address
from delivery.models import DeliveryPerson, DeliverySchedule, DeliverySlot
from orders.models import Order, OrderStatus
from users.models import User


class DeliveryPersonAPITests(APITestCase):
    def setUp(self):
        self.super_admin = User.objects.create(
            mobile='9000000001',
            email='admin@example.com',
            role=User.Role.SUPER_ADMIN,
            is_staff=True,
            is_superuser=True,
        )
        self.super_admin.set_password('AdminPass123')
        self.super_admin.save()

        self.customer = User.objects.create(
            mobile='9000000002',
            email='customer@example.com',
            first_name='Customer',
            role=User.Role.USER,
            profile_complete=True,
        )
        self.address = Address.objects.create(
            user=self.customer,
            full_name='Customer Name',
            mobile='9000000002',
            pincode='500001',
            address_line1='Test Street',
            city='Hyderabad',
            state='Telangana',
        )

    def create_delivery_person(self):
        self.client.force_authenticate(self.super_admin)
        response = self.client.post(
            '/api/v1/admin/delivery-persons/',
            {
                'name': 'Ramesh',
                'phone_number': '9000000003',
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return (
            DeliveryPerson.objects.select_related('user').get(user__mobile='9000000003'),
            response.data['temporary_password'],
        )

    def test_admin_creates_delivery_person_account(self):
        profile, temporary_password = self.create_delivery_person()
        self.assertEqual(profile.user.role, User.Role.DELIVERY_PERSON)
        self.assertFalse(profile.user.profile_complete)
        self.assertTrue(profile.user.check_password(temporary_password))

    def test_delivery_person_completes_profile_and_logs_in(self):
        profile, temporary_password = self.create_delivery_person()
        self.client.force_authenticate(profile.user)
        response = self.client.patch(
            '/api/v1/delivery/me/',
            {
                'name': 'Ramesh Kumar',
                'email': 'ramesh@example.com',
                'vehicle_type': 'Bike',
                'vehicle_number': 'TS09AB1234',
                'address': 'Hyderabad',
                'status': DeliveryPerson.Status.ON_DUTY,
            },
            format='json',
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        profile.user.refresh_from_db()
        self.assertTrue(profile.user.profile_complete)

        self.client.force_authenticate(user=None)
        login_response = self.client.post(
            '/api/v1/delivery/login/',
            {'username': '9000000003', 'password': temporary_password},
            format='json',
        )
        self.assertEqual(login_response.status_code, status.HTTP_200_OK)

    def test_delivery_person_updates_assigned_order_status(self):
        profile, _ = self.create_delivery_person()
        profile.vehicle_type = 'Bike'
        profile.vehicle_number = 'TS09AB1234'
        profile.address = 'Hyderabad'
        profile.status = DeliveryPerson.Status.ON_DUTY
        profile.save()
        profile.user.profile_complete = True
        profile.user.save(update_fields=['profile_complete'])

        assigned = OrderStatus.objects.create(name='Assign to Delivery Partner')
        out_for_delivery = OrderStatus.objects.create(name='Out For Delivery')
        delivered = OrderStatus.objects.create(name='Delivered')
        order = Order.objects.create(
            user=self.customer,
            address=self.address,
            status=assigned,
            delivery_person=profile,
        )

        self.client.force_authenticate(profile.user)
        list_response = self.client.get('/api/v1/delivery/my-orders/')
        self.assertEqual(list_response.status_code, status.HTTP_200_OK)

        status_response = self.client.patch(
            f'/api/v1/delivery/my-orders/{order.order_id}/status/',
            {'status': out_for_delivery.id},
            format='json',
        )
        self.assertEqual(status_response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.status, out_for_delivery)

        delivered_response = self.client.patch(
            f'/api/v1/delivery/my-orders/{order.order_id}/status/',
            {'status': delivered.name},
            format='json',
        )
        self.assertEqual(delivered_response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        self.assertEqual(order.status, delivered)

    def test_admin_assigns_delivery_person_with_slot_and_order_id(self):
        profile, _ = self.create_delivery_person()
        profile.vehicle_type = 'Bike'
        profile.vehicle_number = 'TS09AB1234'
        profile.address = 'Hyderabad'
        profile.status = DeliveryPerson.Status.ON_DUTY
        profile.save()
        profile.user.profile_complete = True
        profile.user.save(update_fields=['profile_complete'])

        placed = OrderStatus.objects.create(name='Placed')
        delivery_date = timezone.localdate() + timedelta(days=2)
        order = Order.objects.create(
            user=self.customer,
            address=self.address,
            status=placed,
        )
        slot = DeliverySlot.objects.create(
            name='Morning',
            start_time='09:00',
            end_time='11:00',
            is_active=True,
        )

        self.client.force_authenticate(self.super_admin)
        response = self.client.post(
            '/api/v1/admin/assign-delivery/',
            {
                'order_id': order.order_id,
                'delivery_slot_id': slot.id,
                'delivery_person_id': profile.id,
                'delivery_date': delivery_date.isoformat(),
            },
            format='json',
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        order.refresh_from_db()
        schedule = DeliverySchedule.objects.get(delivery_date=delivery_date, slot=slot)
        self.assertEqual(order.delivery_person, profile)
        self.assertEqual(order.delivery_schedule, schedule)
        self.assertEqual(order.delivery_date, delivery_date)
        self.assertEqual(order.delivery_slot_name, slot.name)
        self.assertEqual(schedule.booked_orders, 1)
        self.assertEqual(order.status.name, 'Assign to Delivery Partner')
