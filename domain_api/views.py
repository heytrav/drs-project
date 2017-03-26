from __future__ import absolute_import, unicode_literals
import idna
from celery import chain, group
from django_logging import log, ErrorLogObject
from django.db.models import Q
from django.shortcuts import get_object_or_404
# Remove this
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from rest_framework import status, permissions, viewsets, generics
from rest_framework.decorators import (
    api_view,
    permission_classes,
    detail_route,
)
from rest_framework.response import Response
from domain_api.models import (
    Domain,
    AccountDetail,
    ContactType,
    TopLevelDomain,
    DomainProvider,
    Registrant,
    Contact,
    RegisteredDomain,
    DomainRegistrant,
    DomainContact,
    TopLevelDomainProvider,
    DefaultAccountTemplate
)
from domain_api.serializers import (
    UserSerializer,
    AccountDetailSerializer,
    ContactTypeSerializer,
    ContactSerializer,
    TopLevelDomainSerializer,
    TopLevelDomainProviderSerializer,
    DomainProviderSerializer,
    RegistrantSerializer,
    DomainSerializer,
    RegisteredDomainSerializer,
    DomainAvailabilitySerializer,
    HostAvailabilitySerializer,
    DomainRegistrantSerializer,
    DomainContactSerializer,
    InfoDomainSerializer,
    OwnerInfoDomainSerializer,
    PrivateInfoDomainSerializer,
    InfoContactSerializer,
    PrivateInfoContactSerializer,
    DefaultAccountTemplateSerializer,
)
from domain_api.filters import (
    IsPersonFilterBackend
)
from .epp.queries import Domain as DomainQuery, ContactQuery, HostQuery
from .exceptions import (
    EppError,
    InvalidTld,
    UnsupportedTld,
    UnknownRegistry,
    DomainNotAvailable,
    NotObjectOwner,
    EppObjectDoesNotExist
)
from domain_api.entity_management.contacts import ContactFactory
from domain_api.utilities.domain import parse_domain, synchronise_domain
from .workflows import workflow_factory


def process_workflow_chain(chained_workflow):
    """
    Process results of workflow chain.

    :workflow_chain: chain workflow
    :returns: value of last item in chain

    """
    try:
        values = [node.get() for node in reversed(list(workflow_scan(chained_workflow)))]
        return values[-1]
    except KeyError as e:
        log.error({"keyerror": str(e)})
    except Exception as e:
        exception_type = type(e).__name__
        message = str(e)
        if "DomainNotAvailable" in exception_type:
            raise DomainNotAvailable(message)
        elif "NotObjectOwner" in exception_type:
            raise NotObjectOwner(message)
        else:
            raise e


def workflow_scan(node):
    """
    Generate a list of workflow nodes.
    """
    while node.parent:
        yield node
        node = node.parent
    yield node


@api_view(['POST'])
@permission_classes((permissions.IsAdminUser,))
def registry_contact(request, registry, contact_type="contact"):
    """
    Create or view contacts for a particular registry.

    :registry: Registry to add this contact for
    :returns: A contact object
    """
    provider = get_object_or_404(DomainProvider.objects.all(), slug=registry)

    data = request.data
    log.debug(data)
    person = None
    queryset = AccountDetail.objects.all()
    if "person" in data:
        person = get_object_or_404(queryset, pk=data["person"])
    else:
        serializer = AccountDetailSerializer(data=data)
        if serializer.is_valid():
            person = serializer.save(project_id=request.user)
        else:
            return Response(serializer.errors,
                            status=status.HTTP_400_BAD_REQUEST)

    try:
        contact_factory = ContactFactory(provider,
                                         contact_type,
                                         context={"request": request})
        serializer = contact_factory.create_registry_contact(person)
        return Response(serializer.data)
    except EppError as epp_e:
        log.error(ErrorLogObject(request, epp_e))
        return Response(status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        log.error(ErrorLogObject(request, e))
        return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CreateUserView(generics.CreateAPIView):

    """
    Create a user.
    """
    model = get_user_model()
    permission_classes = [ permissions.AllowAny,]
    serializer_class = UserSerializer

class ContactManagementViewSet(viewsets.GenericViewSet):
    """
    Handle contact related queries.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PrivateInfoContactSerializer
    queryset = Contact.objects.all()

    def is_admin_or_owner(self, contact=None):
        """
        Determine if the current logged in user is admin or the owner of
        the object.

        :contact: Contact/Registrant object
        :returns: True or False

        """
        if self.request.user.groups.filter(name='admin').exists():
            log.debug({"msg": "User is admin"})
            return True
        if contact and contact.project_id == self.request.user:
            log.debug({"msg": "Contact exists and owns " + contact.registry_id})
            return True
        return False

    def info(self, request, registry_id, registry=None):
        """
        Retrieve info about a contact

        :request: HTTP request
        :registry_id: registry id
        :returns: InfoContactSerialised response

        """
        try:
            contact = self.get_queryset().get(registry_id=registry_id)

            if self.is_admin_or_owner(contact):
                log.debug({"msg": "Performing info query"})
                query = ContactQuery(self.get_queryset())
                contact = query.info(contact)
                serializer = self.serializer_class(contact)
                return Response(serializer.data)
            else:
                log.debug({"msg": "Returning basic contact info"})
                contact_data = {
                    "registry_id": contact.registry_id,
                }
                if contact.disclose_name:
                    contact_data["name"] = contact.name
                if contact.disclose_email:
                    contact_data["email"] = contact.email
                if contact.disclose_telephone:
                    contact_data["telephone"] = contact.telephone
                if contact.disclose_fax:
                    contact_data["fax"] = contact.fax
                if contact.disclose_company:
                    contact_data["company"] = contact.company
                if contact.disclose_address:
                    contact_data["street1"] = contact.street1
                    contact_data["street2"] = contact.street2
                    contact_data["street3"] = contact.street3
                    contact_data["city"] = contact.city
                    contact_data["house_number"] = contact.house_number
                    contact_data["country"] = contact.country
                    contact_data["state"] = contact.state
                    contact_data["postcode"] = contact.postcode
                    contact_data["postal_info_type"] = contact.postal_info_type
                serializer = InfoContactSerializer(data=contact_data)
                if serializer.is_valid():
                    log.debug(serializer.data)
                    return Response(serializer.data)
                else:
                    log.error(serializer.errors)
                    return Response(serializer.errors)

        except UnknownRegistry as e:
            log.error(ErrorLogObject(request, e))
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except EppError as epp_e:
            log.error(ErrorLogObject(request, epp_e))
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            log.error(ErrorLogObject(request, e))
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def list(self, request):
        """
        List out contact/registrant objects

        :request: HTTP request object
        :returns: InfoContactSerializer response

        """
        contacts = self.get_queryset()
        if not self.is_admin_or_owner():
            contacts = contacts.filter(project_id=self.request.user)

        serializer = InfoContactSerializer(contacts, many=True)
        return Response(serializer.data)

class RegistrantManagementViewSet(ContactManagementViewSet):
    """
    Handle registrant related queries.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PrivateInfoContactSerializer
    queryset = Registrant.objects.all()

class HostManagementViewSet(viewsets.GenericViewSet):

    """
    Handle nameserver related queries.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        Return queryset
        :returns: queryset object

        """
        queryset = NameserverHost.objects.all()
        user = self.request.user
        if user.groups.filter(name='admin').exists():
            return queryset
        return queryset.filter(project_id=user).distinct()

    def available(self, request, host=None):
        """
        Check availability of host.

        :request: HTTP request
        :returns: availability of host object

        """
        try:
            query = HostQuery()
            availability = query.check_host(
                idna.encode(host, uts46=True).decode('ascii')
            )
            serializer = HostAvailabilitySerializer(data=availability["result"][0])
            if serializer.is_valid():
                return Response(serializer.data)
        except EppError as epp_e:
            log.error(ErrorLogObject(request, epp_e))
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except KeyError as ke:
            log.error(ErrorLogObject(request, ke))
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            raise e

    def create(self, request):
        """
        Register a nameserver host.

        :request: Request object with JSON payload
        :returns: Response from registry
        """
        data = request.data
        chain_res = None
        try:
            # See if this TLD is provided by one of our registries.
            registry = get_domain_registry(data["host"])
            workflow_manager = workflow_factory(registry)()

            log.debug({"msg": "About to call workflow_manager.create_domain"})
            workflow = workflow_manager.create_host(data, request.user)
            # run chained workflow and register the domain
            chained_workflow = chain(workflow)()
            chain_res = process_workflow_chain(chained_workflow)
            serializer = InfoDomainSerializer(data=chain_res)
            if serializer.is_valid():
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                log.error(serializer.errors)
                return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response(chain_res)
        except DomainNotAvailable:
            return Response("Domain not available",
                            status=status.HTTP_400_BAD_REQUEST)
        except NotObjectOwner:
            return Response("Not owner of object",
                            status=status.HTTP_400_BAD_REQUEST)
        except KeyError as e:
            log.error(ErrorLogObject(request, e))
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except TopLevelDomainProvider.DoesNotExist:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            log.error(ErrorLogObject(request, e))
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class DomainRegistryManagementViewSet(viewsets.GenericViewSet):
    """
    Handle domain related queries.
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PrivateInfoDomainSerializer

    def get_queryset(self):
        """
        Return queryset
        :returns: RegisteredDomain set
        """
        queryset = RegisteredDomain.objects.all()
        user = self.request.user
        if user.groups.filter(name='admin').exists():
            return queryset
        return queryset.filter(
            Q(registrant__registrant__project_id=user) |
            Q(contacts__contact__project_id=user)
        ).distinct()

    def is_admin_or_owner(self, domain=None):
        """
        Determine if the current logged in user is admin or the owner of
        the object.

        :domain: Contact/Registrant object
        :returns: True or False

        """
        user = self.request.user
        # Check if user is admin
        if user.groups.filter(name='admin').exists():
            return True
        # otherwise check if user is registrant of contact for domain
        if domain:
            if domain.registrant.filter(active=True, registrant__project_id=user):
                return True
            if domain.contacts.contact.filter(project_id=user).exists():
                return True
        return False

    @detail_route(methods=['get'])
    def available(self, request, domain=None):
        """
        Check availability of a domain name

        :request: HTTP request
        :domain: str domain name to check
        :returns: availability of domain object

        """
        try:
            query = DomainQuery()
            availability = query.check_domain(
                idna.encode(domain, uts46=True).decode('ascii')
            )
            serializer = DomainAvailabilitySerializer(data=availability["result"][0])
            if serializer.is_valid():
                return Response(serializer.data)
        except EppError as epp_e:
            log.error(ErrorLogObject(request, epp_e))
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except KeyError as ke:
            log.error(ErrorLogObject(request, ke))
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @detail_route(methods=['get'])
    def bulk_available(self, request, name=None):
        """
        Check availability of a domain name

        :request: HTTP request
        :name: str domain name to check
        :returns: availability of domain object

        """
        try:
            providers = DomainProvider.objects.all()
            registry_workflows = []
            for provider in providers.all():
                provider_slug = provider.slug
                workflow_manager = workflow_factory(provider_slug)()
                tld_providers = provider.topleveldomainprovider_set.all()
                fqdn_list = []
                for tld_provider in tld_providers.all():
                    zone = tld_provider.zone.zone
                    fqdn_list.append(".".join(
                        [
                            idna.encode(name, uts46=True).decode('ascii'),
                            zone
                        ]
                    )
                    )
                check_task = workflow_manager.check_domains(
                    fqdn_list
                )
                registry_workflows.append(check_task)
            check_group = group(registry_workflows)()
            registry_result = check_group.get()
            check_result = []
            for i in registry_result:
                check_result += i
            log.info({"result": check_result})
            serializer = DomainAvailabilitySerializer(data=check_result, many=True)
            if serializer.is_valid():
                return Response(serializer.data)
            else:
                return Response(serializer.errors,
                                status=status.HTTP_400_BAD_REQUEST)

        except EppError as epp_e:
            log.error(ErrorLogObject(request, epp_e))
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except KeyError as ke:
            log.error(ErrorLogObject(request, ke))
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def domain_set(self, request):
        """
        Query for domains linked to a particular registry contact
        :returns: JSON response with details about a contact

        """
        try:
            # Limit registered domain query to "owned" domains
            registered_domain_set = self.get_queryset()
            contact_domains = registered_domain_set.filter(active=True)
            serializer = self.serializer_class(contact_domains, many=True)
            return Response(serializer.data)
        except Exception as e:
            log.error(ErrorLogObject(request, e))
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def info(self, request, domain):
        """
        Query EPP with a infoDomain request.


        :request: HTTP request
        :domain: str domain name to check
        :returns: JSON response with details about a domain

        """
        try:
            # Fetch registry for domain
            query = DomainQuery(self.get_queryset())
            info, registered_domain = query.info(domain)
            log.info(info)
            if registered_domain and self.is_admin_or_owner(registered_domain):
                synchronise_domain(info, registered_domain.id)
                serializer = self.serializer_class(
                    self.get_queryset().get(pk=registered_domain.id)
                )
                return Response(serializer.data)
            serializer = InfoDomainSerializer(data=info)
            if serializer.is_valid():
                return Response(serializer.data)
            else:
                return Response(serializer.errors,
                                status=status.HTTP_400_BAD_REQUEST)
        except InvalidTld as e:
            log.error(ErrorLogObject(request, e))
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except UnsupportedTld as e:
            log.error(ErrorLogObject(request, e))
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except EppObjectDoesNotExist as epp_e:
            log.error(ErrorLogObject(request, epp_e))
            return Response(status=status.HTTP_404_NOT_FOUND)
        except EppError as epp_e:
            log.error(ErrorLogObject(request, epp_e))
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            log.error(ErrorLogObject(request, e))
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def create(self, request):
        """
        Register a domain name.

        :request: Request object with JSON payload
        :returns: Response from registry
        """
        data = request.data
        parsed_domain = parse_domain(data["domain"])
        chain_res = None
        try:
            # See if this TLD is provided by one of our registries.
            tld_provider = TopLevelDomainProvider.objects.get(
                zone__zone=parsed_domain["zone"]
            )
            registry = tld_provider.provider.slug
            workflow_manager = workflow_factory(registry)()

            log.debug({"msg": "About to call workflow_manager.create_domain"})
            workflow = workflow_manager.create_domain(data, request.user)
            # run chained workflow and register the domain
            chained_workflow = chain(workflow)()
            chain_res = process_workflow_chain(chained_workflow)
            serializer = InfoDomainSerializer(data=chain_res)
            if serializer.is_valid():
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            else:
                log.error(serializer.errors)
                return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            return Response(chain_res)
        except DomainNotAvailable:
            return Response("Domain not available",
                            status=status.HTTP_400_BAD_REQUEST)
        except NotObjectOwner:
            return Response("Not owner of object",
                            status=status.HTTP_400_BAD_REQUEST)
        except KeyError as e:
            log.error(ErrorLogObject(request, e))
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except TopLevelDomainProvider.DoesNotExist:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            log.error(ErrorLogObject(request, e))
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AccountDetailViewSet(viewsets.ModelViewSet):
    serializer_class = AccountDetailSerializer
    permission_classes = (permissions.IsAuthenticated,
                          permissions.DjangoModelPermissionsOrAnonReadOnly,)

    def perform_create(self, serializer):
        serializer.save(project_id=self.request.user)

    def get_queryset(self):
        """
        Override to make sure that this only returns personal details that
        belong to logged in user.
        :returns: Filtered set of personal detail objects.

        """
        user = self.request.user
        if user.is_staff:
            return AccountDetail.objects.all()
        return AccountDetail.objects.filter(project_id=user)


class UserViewSet(viewsets.ReadOnlyModelViewSet):

    """
    This viewset automatically provides `list` and `detail` actions.
    """
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = (permissions.IsAdminUser,)


class ContactTypeViewSet(viewsets.ModelViewSet):

    """
    Contact type view
    """
    queryset = ContactType.objects.all()
    serializer_class = ContactTypeSerializer
    permission_classes = (permissions.DjangoModelPermissionsOrAnonReadOnly,)
    lookup_field = 'name'


class TopLevelDomainViewSet(viewsets.ModelViewSet):
    """
    Set of top level domains.
    """

    queryset = TopLevelDomain.objects.all()
    serializer_class = TopLevelDomainSerializer
    permission_classes = (permissions.DjangoModelPermissionsOrAnonReadOnly,)
    lookup_field = 'zone'


class DomainProviderViewSet(viewsets.ModelViewSet):
    """
    Set of tld providers.
    """

    queryset = DomainProvider.objects.all()
    serializer_class = DomainProviderSerializer
    permission_classes = (permissions.DjangoModelPermissionsOrAnonReadOnly,)
    lookup_field = 'slug'


class ContactViewSet(viewsets.ModelViewSet):
    """
    Contact handles.
    """

    serializer_class = ContactSerializer
    permission_classes = (permissions.DjangoModelPermissionsOrAnonReadOnly,
                          permissions.IsAuthenticated)
    filter_backends = (IsPersonFilterBackend,)
    lookup_field = 'registry_id'

    def get_queryset(self):
        """
        Override to make sure that this only returns personal details that
        belong to logged in user.
        :returns: Filtered set of personal detail objects.

        """
        user = self.request.user
        if user.is_staff:
            return Contact.objects.all()
        return Contact.objects.filter(project_id=user)


class TopLevelDomainProviderViewSet(viewsets.ModelViewSet):

    queryset = TopLevelDomainProvider.objects.all()
    serializer_class = TopLevelDomainProviderSerializer
    permission_classes = (permissions.IsAdminUser,)


class RegistrantViewSet(viewsets.ModelViewSet):

    serializer_class = RegistrantSerializer
    permission_classes = (permissions.IsAuthenticated,)
    lookup_field = 'registry_id'

    def get_queryset(self):
        """
        Override to make sure that this only returns personal details that
        belong to logged in user.
        :returns: Filtered set of personal detail objects.

        """
        user = self.request.user
        if user.is_staff:
            return Registrant.objects.all()
        return Registrant.objects.filter(project_id=user)


class DomainViewSet(viewsets.ModelViewSet):

    serializer_class = DomainSerializer
    permission_classes = (permissions.IsAuthenticated,)
    queryset = Domain.objects.all()
    lookup_field = 'name'


class RegisteredDomainViewSet(viewsets.ModelViewSet):

    serializer_class = RegisteredDomainSerializer
    permission_classes = (permissions.IsAuthenticated,
                          permissions.DjangoModelPermissionsOrAnonReadOnly,)
    queryset = RegisteredDomain.objects.all()


class DomainRegistrantViewSet(viewsets.ModelViewSet):

    serializer_class = DomainRegistrantSerializer
    permission_classes = (permissions.IsAuthenticated,
                          permissions.DjangoModelPermissionsOrAnonReadOnly,)

    def get_queryset(self):
        """
        Filter registered domains on request user.
        :returns: Set of RegisteredDomain objects filtered by customer

        """
        user = self.request.user
        if user.is_staff:
            return DomainRegistrant.objects.all()
        return DomainRegistrant.objects.filter(registrant__project_id=user)


class DomainContactViewSet(viewsets.ModelViewSet):

    serializer_class = DomainContactSerializer
    permission_classes = (permissions.IsAuthenticated,
                          permissions.DjangoModelPermissionsOrAnonReadOnly,)

    def get_queryset(self):
        """
        Filter domain handles on logged in user.
        :returns: Set of DomainContact objects filtered by customer

        """
        user = self.request.user
        if user.is_staff:
            return DomainContact.objects.all()
        return DomainContact.objects.filter(contact__project_id=user)


class DefaultAccountTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = DefaultAccountTemplateSerializer
    permission_classes = (permissions.IsAuthenticated,
                          permissions.DjangoModelPermissionsOrAnonReadOnly)


    def create(self, request):
        """
        Create a new default template

        :request: HTTP request object
        :returns: HTTP response

        """
        data = request.data
        serializer = self.serializer_class(data=data)
        if serializer.is_valid():
            account_templates = AccountDetail.objects.filter(
                project_id=request.user
            )
            account_template = get_object_or_404(account_templates,
                                                 pk=data["account_template"])
            serializer.save(
                project_id=request.user,
                account_template=account_template,
                provider=DomainProvider.objects.get(slug=data["provider"])
            )
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def update(self, request, default_id):
        """
        Update a default account template

        """
        default_account_template = get_object_or_404(self.get_queryset(),
                                                     default_id)
        data = request.data
        account_templates = AccountDetail.objects.filter(
            project_id=request.user
        )
        account_template = get_object_or_404(account_templates,
                                             pk=data["account_template"])
        default_account_template.update(account_template=account_template,
                                        provider=data["provider"])


    def delete(self, request, default_id):
        """
        Delete a default template

        """
        default_account_template = get_object_or_404(self.get_queryset(),
                                                     pk=default_id)
        default_account_template.delete()

    def detail(self, request, default_id):
        """
        Retrieve single object

        """
        log.debug({"default_id": default_id})
        default_account_template = get_object_or_404(self.get_queryset(),
                                                     pk=default_id)
        serializer = self.serializer_class(default_account_template,
                                           context={"request": request})
        return Response(serializer.data)

    def list(self, request):
        """
        Return list of default accounts

        :request: HTTP request object
        :returns: DefaultAccountTemplateSerializer

        """
        account_templates = self.get_queryset()
        serializer = self.serializer_class(account_templates,
                                           context={"request": request},
                                           many=True)
        return Response(serializer.data)

    def get_queryset(self):
        """
        Filter domain handles on logged in user.
        :returns: Set of DomainContact objects filtered by customer

        """
        user = self.request.user
        if user.is_staff:
            return DefaultAccountTemplate.objects.all()
        return DefaultAccountTemplate.objects.filter(project_id=user)


class DefaultAccountContactViewSet(viewsets.ModelViewSet):
    serializer_class = DefaultAccountTemplateSerializer
    permission_classes = (permissions.IsAdminUser,)


    def get_queryset(self):
        """
        Filter domain handles on logged in user.
        :returns: Set of DomainContact objects filtered by customer

        """
        user = self.request.user
        if user.is_staff:
            return DefaultAccountContact.objects.all()
        return DefaultAccountContact.objects.filter(project_id=user)

    #def perform_create(self, serializer):

        #data = self.request.data
        #provider_slug = data["provider"]
        #provider = DomainProvider.objects.get(slug=provider_slug)
        #serializer.save(project_id=self.request.user, provider=provider)
