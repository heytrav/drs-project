from __future__ import absolute_import, unicode_literals
from celery import shared_task
from django.contrib.auth.models import User
from django_logging import log, ErrorLogObject
from .models import (
    Contact,
    ContactType,
    Domain,
    DomainContact,
    DomainProvider,
    DomainRegistrant,
    PersonalDetail,
    RegisteredDomain,
    Registrant,
    TopLevelDomain,
    TopLevelDomainProvider
)
from .entity_management.contacts import RegistrantManager, ContactManager
from .epp.actions.domain import Domain as DomainAction
from .epp.queries import Domain as DomainQuery
from .utilities.domain import parse_domain, get_domain_registry
from .exceptions import (
    DomainNotAvailable,
    NotObjectOwner
)

@shared_task
def check_bulk_domain(registry, domains):
    """
    Bulk domain check

    :domains: set of domains
    :registry: registry to query
    :returns: dict result from provider

    """
    query = DomainQuery()
    availability = query.check_domain(registry, domains)
    return availability["result"]

@shared_task
def check_domain(domain):
    """
    Check if a domain exists.

    :domain: FQDN to check
    :returns: boolean

    """
    provider = get_domain_registry(domain)
    registry = provider.slug
    log.info({"command": "check_domain",
              "domain": domain,
              "registry": registry})
    query = DomainQuery()
    availability = query.check_domain(registry, domain)
    available = availability["result"][0]["available"]
    log.info({"available": available})
    if str(available) == "1" or str(available) == "true" or available == True:
        return True
    raise DomainNotAvailable("%s not available" % domain)


@shared_task
def create_registrant(epp,
                      person_id=None,
                      registry=None,
                      user=None,
                      force=False):
    """
    Create a new contact at a registry. If a contact handle matching the
    person id and the registry already exists, use that one.

    :person_id: Integer identifying a person
    :registry: Registry slug to identify registry
    :force: Boolean value
    :returns: registry id of new contact.

    """
    provider = DomainProvider.objects.get(slug=registry)
    person = PersonalDetail.objects.get(pk=person_id)
    user_obj = User.objects.get(pk=user)
    contact_manager = RegistrantManager(provider, person, user_obj)
    contact = contact_manager.fetch_existing_contact()
    if not contact or force:
        contact = contact_manager.create_registry_contact()
    epp["registrant"] = contact.registry_id
    return epp


@shared_task
def create_registry_contact(epp,
                            person_id=None,
                            registry=None,
                            contact_type="contact",
                            user=None,
                            force=False):
    """
    Create a new contact at a registry. If a contact handle matching the
    person id and the registry already exists, use that one.

    :person_id: Integer identifying a person
    :registry: Registry slug to identify registry
    :force: Boolean value
    :returns: registry id of new contact.

    """
    contacts = epp.get("contact", [])

    provider = DomainProvider.objects.get(slug=registry)
    person = PersonalDetail.objects.get(pk=person_id)
    user_obj = User.objects.get(pk=user)
    contact_manager = ContactManager(provider, person, user_obj)
    contact_obj = contact_manager.fetch_existing_contact()
    if not contact_obj or force:
        contact_obj = contact_manager.create_registry_contact()

    log.info({"contact_handle": contact_obj.registry_id})
    contact = {}
    contact[contact_type] = contact_obj.registry_id
    contacts.append(contact)
    epp["contact"] = contacts
    return epp


@shared_task
def create_domain(epp, registry):
    """
    Create a domain at a given registry

    :epp: raw epp command
    :returns: success or fail

    """
    domain = DomainAction()
    result = domain.create(registry, epp)
    return {**epp, **result}

@shared_task
def connect_domain(create_data, user=None):
    """
    Connect the newly created domain in our database.

    :create_data: The epp request and response information
    :returns: dict with EPP response

    """
    try:
        parsed_domain = parse_domain(create_data["name"])
        domain_obj, _ = Domain.objects.get_or_create(
            name=parsed_domain["domain"],
            idn=parsed_domain["domain"]
        )
        tld_provider = TopLevelDomainProvider.objects.get(
            zone__zone=parsed_domain["zone"]
        )
        tld = TopLevelDomain.objects.get(zone=parsed_domain["zone"])
        registered_domain = RegisteredDomain(
            domain=domain_obj,
            tld=tld,
            tld_provider=tld_provider,
            registration_period=1,
            anniversary=create_data["expiration_date"],
            created=create_data["create_date"],
            active=True
        )
        registered_domain.save()
        registrant = Registrant.objects.get(registry_id=create_data["registrant"])
        registered_domain.registrant.create(
            registrant=registrant,
            active=True,
        )
        for item in create_data["contact"]:
            (con_type, registry_id), = item.items()
            contact_type = ContactType.objects.get(name=con_type)
            contact = Contact.objects.get(registry_id=registry_id)
            registered_domain.contacts.create(
                contact=contact,
                contact_type=contact_type,
                active=True
            )
        return create_data
    except Exception as e:
        log.error({"error": e})
        raise e
