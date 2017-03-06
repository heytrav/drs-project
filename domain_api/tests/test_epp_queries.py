from django.contrib.auth.models import User
from django.test import TestCase
from unittest.mock import patch
from domain_api.epp.queries import ContactQuery
from domain_api.epp.entity import EppRpcClient
from domain_api.models import (
    Contact,
    DomainProvider,
)
import domain_api


class MockRpcClient(domain_api.epp.entity.EppRpcClient):
    def __init__(self, host=None):
        pass


class TestCheckDomain(TestCase):

    """
    Test processing of check domain.
    """

    @patch('domain_api.epp.entity.EppRpcClient', new=MockRpcClient)
    def test_bulk_check_domain(self):
        self.assertTrue(True)


class TestInfoContact(TestCase):

    """
    Test processing info contact.
    """

    def setUp(self):
        super().setUp()
        self.user = User.objects.create_user(
            username="testcustomer",
            email="testcustomer@test.com",
            password="secret"
        )
        self.provider = DomainProvider(
            name="Provider One",
            slug="provider1"
        )
        self.provider.save()
        self.contact = Contact(
            registry_id='test-contact',
            project_id=self.user,
            provider=self.provider
        )
        self.contact.save()

    @patch('domain_api.epp.entity.EppRpcClient', new=MockRpcClient)
    def test_info_domain(self):
        """
        Test info domain processing.
        """
        info_contact_response = {
            "contact:infData": {
                "contact:authInfo": {
                    "contact:pw": "iafbv5yoe5cg4k8cww44kk0400wg8gg"
                },
                "contact:clID": "H93060719",
                "contact:crDate": "2017-01-23T02:48:25.0Z",
                "contact:crID": "H93060719",
                "contact:disclose": {
                    "contact:addr": {
                        "type": "int"
                    },
                    "contact:email": {},
                    "contact:fax": {},
                    "contact:name": {
                        "type": "int"
                    },
                    "contact:org": {
                        "type": "int"
                    },
                    "contact:voice": {},
                    "flag": "1"
                },
                "contact:email": "joe-test@testerson.com",
                "contact:fax": {},
                "contact:id": "reg-20",
                "contact:postalInfo": {
                    "contact:addr": {
                        "contact:cc": "US",
                        "contact:city": "Boston",
                        "contact:pc": "23433",
                        "contact:sp": "MA",
                        "contact:street": "Paralala Street"
                    },
                    "contact:name": "Joe User",
                    "contact:org": {},
                    "type": "int"
                },
                "contact:roid": "C112983065-CNIC",
                "contact:status": {
                    "s": "ok"
                },
                "contact:upDate": "2017-02-09T10:11:31.0Z",
                "contact:voice": "+64.11223344",
                "xmlns:contact": "urn:ietf:params:xml:ns:contact-1.0"
            }
        }
        contact_query = ContactQuery(self.user,
                                     Contact.objects.filter(project_id=self.user))
        with patch.object(EppRpcClient,
                          'call',
                          return_value=info_contact_response):
            info_data = contact_query.info("test-contact",
                                           'test-registry')
            self.assertIn('email',
                          info_data,
                          "Response from info request contains email")
            self.assertEqual(info_data["registry_id"],
                             "reg-20",
                             "contact id is expected value")
            self.assertEqual(info_data["country"], "US", "Expected country US")
