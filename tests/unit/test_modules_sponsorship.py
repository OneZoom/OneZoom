"""
Run with
python3 /srv/devel/onezoom/web2py.py \
    -S OZtree -M -R applications/OZtree/tests/unit/test_modules_sponsorship.py
"""
import datetime
import unittest

from gluon.globals import Request

from sponsorship import (
    add_reservation,
    sponsorable_children_query,
    sponsorship_enabled,
    reservation_add_to_basket,
    reservation_confirm_payment,
)


class TestSponsorship(unittest.TestCase):
    def setUp(self):
        request = Request(dict())
        clear_unittest_sponsors()

        # Allow sponsorship by default
        set_allow_sponsorship(1)
        self.assertEqual(sponsorship_enabled(), True)

    def tearDown(self):
        clear_unittest_sponsors()

    def test_add_reservation__invalid(self):
        """Invalid OTT is invalid"""
        status, reservation_row = add_reservation(-1000, form_reservation_code="UT::001")
        self.assertEqual(status, 'invalid')

    def test_add_reservation__reserve(self):
        """Can reserve items if sponsorship enabled"""
        # Sponsorship should be off
        set_allow_sponsorship(0)
        self.assertEqual(sponsorship_enabled(), False)

        # Anyone sees an empty item as available
        ott = find_unsponsored_ott()
        status, reservation_row = add_reservation(ott, form_reservation_code="UT::001")
        self.assertEqual(status, 'available')
        self.assertEqual(reservation_row.OTT_ID, ott)
        status, reservation_row = add_reservation(ott, form_reservation_code="UT::002")
        self.assertEqual(status, 'available')
        self.assertEqual(reservation_row.OTT_ID, ott)

        # Sponsorship activate
        set_allow_sponsorship(1)
        self.assertEqual(sponsorship_enabled(), True)

        # Can reserve an OTT, and re-request it
        ott = find_unsponsored_ott()
        status, reservation_row = add_reservation(ott, form_reservation_code="UT::001")
        self.assertEqual(status, 'available')
        self.assertEqual(reservation_row.OTT_ID, ott)
        status, reservation_row = add_reservation(ott, form_reservation_code="UT::001")
        self.assertEqual(status, 'available only to user')
        self.assertEqual(reservation_row.OTT_ID, ott)

        # Another user can't get it now, but can tomorrow
        status, reservation_row = add_reservation(ott, form_reservation_code="UT::002")
        self.assertEqual(status, 'reserved')
        current.request.now = (current.request.now + datetime.timedelta(days=1))
        status, reservation_row = add_reservation(ott, form_reservation_code="UT::002")
        self.assertEqual(status, 'available')

    def test_reservation_confirm_payment__invalid(self):
        """Unknown baskets are an error"""
        with self.assertRaisesRegex(ValueError, r'PP_transaction_code'):
            reservation_confirm_payment("UT::invalid", 1000, dict())

        with self.assertRaisesRegex(ValueError, r'basket_code UT::invalid'):
            reservation_confirm_payment("UT::invalid", 1000, dict(PP_transaction_code='UT::001'))

    def test_reservation_confirm_payment__giftaid(self):
        """Buy a single item with giftaid on/off"""

        # Buy ott1 with giftaid off
        ott1 = find_unsponsored_ott()
        status, reservation_row1 = add_reservation(ott1, form_reservation_code="UT::001")
        self.assertEqual(status, 'available')
        reservation_add_to_basket('UT::BK001', reservation_row1, dict(
            e_mail='001@unittest.example.com',
            user_giftaid=False,
            user_sponsor_name="Arnold",  # NB: Have to at least set user_sponsor_name
        ))
        reservation_confirm_payment('UT::BK001', 10000, dict(
            PP_transaction_code='UT::PP1',
            PP_house_and_street='PP House',
            PP_postcode='PO12 3DE',
            PP_e_mail='paypal@unittest.example.com',
        ))

        # Can't reserve it since it's unverified (not "sponsored" since we haven't set verified)
        status, reservation_row1 = add_reservation(ott1, form_reservation_code="UT::002")
        self.assertEqual(status, 'unverified')
        # E-mail got set, house/postcode didn't
        self.assertEqual(reservation_row1.PP_e_mail, 'paypal@unittest.example.com')
        self.assertEqual(reservation_row1.PP_house_and_street, None)
        self.assertEqual(reservation_row1.PP_postcode, None)

        # Validate row, is fully sponsored
        reservation_row1.update_record(verified_time=current.request.now)
        status, reservation_row1 = add_reservation(ott1, form_reservation_code="UT::002")
        self.assertEqual(status, 'sponsored')

        # Buy ott2 with giftaid on
        ott2 = find_unsponsored_ott()
        status, reservation_row2 = add_reservation(ott2, form_reservation_code="UT::001")
        self.assertEqual(status, 'available')
        reservation_add_to_basket('UT::BK002', reservation_row2, dict(
            e_mail='001@unittest.example.com',
            user_giftaid=True,
            user_sponsor_name="Arnold",  # NB: Have to at least set user_sponsor_name
        ))
        reservation_confirm_payment('UT::BK002', 10000, dict(
            PP_transaction_code='UT::PP2',
            PP_house_and_street='PP House',
            PP_postcode='PO12 3DE',
            PP_e_mail='paypal@unittest.example.com',
        ))

        # Address gets set, old row left alone
        status, reservation_row1 = add_reservation(ott1, form_reservation_code="UT::002")
        self.assertEqual(status, 'sponsored')
        self.assertEqual(reservation_row1.PP_e_mail, 'paypal@unittest.example.com')
        self.assertEqual(reservation_row1.PP_house_and_street, None)
        self.assertEqual(reservation_row1.PP_postcode, None)
        status, reservation_row2 = add_reservation(ott2, form_reservation_code="UT::002")
        self.assertEqual(status, 'unverified')
        self.assertEqual(reservation_row2.PP_e_mail, 'paypal@unittest.example.com')
        self.assertEqual(reservation_row2.PP_house_and_street, "PP House")
        self.assertEqual(reservation_row2.PP_postcode, "PO12 3DE")

    def test_reservation_confirm_payment__renew(self):
        """Buy an item twice to renew it"""

        # Buy ott1
        ott1 = find_unsponsored_ott()
        status, reservation_row = add_reservation(ott1, form_reservation_code="UT::001")
        self.assertEqual(status, 'available')
        reservation_add_to_basket('UT::BK001', reservation_row, dict(
            e_mail='001@unittest.example.com',
            user_sponsor_name="Arnold",  # NB: Have to at least set user_sponsor_name
        ))
        reservation_confirm_payment('UT::BK001', 10000, dict(
            PP_transaction_code='UT::PP1',
            PP_e_mail='paypal@unittest.example.com',
        ))

        # Can't reserve it since it's unverified (not "sponsored" since we haven't set verified)
        status, reservation_row = add_reservation(ott1, form_reservation_code="UT::002")
        self.assertEqual(status, 'unverified')
        # E-mail, asking price got set
        self.assertEqual(reservation_row.PP_e_mail, 'paypal@unittest.example.com')
        self.assertGreater(reservation_row.asking_price, 4)
        orig_asking_price = reservation_row.asking_price

        # Replaying a transaction gets ignored
        reservation_confirm_payment('UT::BK001', 10000, dict(
            PP_transaction_code='UT::PP1',
            PP_e_mail='paypal-replay-attack@unittest.example.com',
        ))
        status, reservation_row = add_reservation(ott1, form_reservation_code="UT::002")
        self.assertEqual(status, 'unverified')
        self.assertEqual(reservation_row.PP_e_mail, 'paypal@unittest.example.com')

        # Validate row, is fully sponsored for 4 years
        reservation_row.update_record(verified_time=current.request.now)
        status, reservation_row = add_reservation(ott1, form_reservation_code="UT::002")
        self.assertEqual(status, 'sponsored')
        self.assertEqual(reservation_row.sponsorship_duration_days, 365 * 4 + 1)
        self.assertLess(
            reservation_row.sponsorship_ends - request.now - datetime.timedelta(days = 365 * 4 + 1),
            datetime.timedelta(minutes=1))

        # ...but can add it to a new basket and renew it.
        reservation_add_to_basket('UT::BK002', reservation_row, dict(
            e_mail='001@unittest.example.com',
            user_sponsor_name="Arnold",  # NB: Have to at least set user_sponsor_name
        ))
        reservation_confirm_payment('UT::BK002', 10000, dict(
            PP_transaction_code='UT::PP2',
            PP_e_mail='paypal-new-addr@unittest.example.com',
        ))

        # Now reserved for 8 years, with updated details
        status, reservation_row = add_reservation(ott1, form_reservation_code="UT::002")
        self.assertEqual(status, 'sponsored')  # NB: Verification status preserved
        self.assertEqual(reservation_row.PP_e_mail, 'paypal-new-addr@unittest.example.com')
        self.assertEqual(reservation_row.sponsorship_duration_days, 365 * 4 + 1)  # NB: Duration still 4 years.
        self.assertLess(
            reservation_row.sponsorship_ends - request.now - datetime.timedelta(days = 365 * 8 + 1),
            datetime.timedelta(minutes=1))

        # The asking price dropped, as it's a renewal
        self.assertEqual(reservation_row.asking_price, orig_asking_price * (1 - 0.2))

        # Can find the old row as an expired reservation
        expired_row = db(
            (db.expired_reservations.OTT_ID == ott1) &
            (db.expired_reservations.PP_transaction_code == 'UT::PP1')).select().first()
        self.assertEqual(expired_row.e_mail, '001@unittest.example.com')
        self.assertEqual(expired_row.PP_e_mail, 'paypal@unittest.example.com')
        self.assertEqual(expired_row.asking_price, orig_asking_price)


def clear_unittest_sponsors():
    """
    Anything with UT:: id or basket_code, or @unittest.example.com e-mail address
    is assumed to be from a test, remove it
    """
    db(
        db.reservations.user_registration_id.startswith('UT::') |
        db.reservations.basket_code.startswith('UT::') |
        db.reservations.e_mail.endswith('@unittest.example.com')).delete()
    db(
        db.expired_reservations.user_registration_id.startswith('UT::') |
        db.expired_reservations.basket_code.startswith('UT::') |
        db.expired_reservations.e_mail.endswith('@unittest.example.com')).delete()


def set_allow_sponsorship(val):
    """Update site config with new value for sponsorship.allow_sponsorship"""
    myconf = current.globalenv['myconf']
    myconf['sponsorship']['allow_sponsorship'] = str(val)
    if 'sponsorship.allow_sponsorship' in myconf.int_cache:
        del myconf.int_cache['sponsorship.allow_sponsorship']


def find_unsponsored_ott():
    query = sponsorable_children_query(147604, qtype="ott")
    r = db(query).select(limitby=(0, 1)).first()
    if r is None:
        raise ValueError("Can't find an available OTT")
    return r.ott


if __name__ == '__main__':
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestSponsorship))
    unittest.TextTestRunner(verbosity=2).run(suite)

