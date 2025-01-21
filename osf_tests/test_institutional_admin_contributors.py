import pytest

from osf.models import Contributor
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    InstitutionFactory,
    NodeRequestFactory
)
from django.db.utils import IntegrityError

@pytest.mark.django_db
class TestContributorModel:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_with_institutional_request(self, project):
        user = AuthUserFactory()
        NodeRequestFactory(
            target=project,
            creator=user,
            is_institutional_request=True,
        )
        return user

    @pytest.fixture()
    def user_with_non_institutional_request(self, project):
        user = AuthUserFactory()
        NodeRequestFactory(
            target=project,
            creator=user,
            is_institutional_request=False,
        )
        return user

    @pytest.fixture()
    def project(self):
        return ProjectFactory()

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def institutional_admin(self, institution):
        admin_user = AuthUserFactory()
        institution.get_group('institutional_admins').user_set.add(admin_user)
        return admin_user

    @pytest.fixture()
    def curator(self, institutional_admin, project):
        return Contributor(
            user=institutional_admin,
            node=project,
            visible=False,
            is_curator=True
        )

    def test_contributor_with_visible_and_pending_request_raises_error(self, user_with_institutional_request, project, institution):
        user_with_institutional_request.save()
        user_with_institutional_request.visible = True
        user_with_institutional_request.refresh_from_db()
        assert user_with_institutional_request.visible

        try:
            project.add_contributor(user_with_institutional_request, make_curator=True)
        except IntegrityError as e:
            assert e.args == ('Curators cannot be made bibliographic contributors',)

    def test_contributor_with_visible_and_valid_request(self, user_with_non_institutional_request, project, institution):
        user_with_non_institutional_request.save()
        user_with_non_institutional_request.visible = True
        user_with_non_institutional_request.save()

        user_with_non_institutional_request.refresh_from_db()
        assert user_with_non_institutional_request.visible

    def test_contributor_with_visible_and_institutional_admin_raises_error(self, curator, project, institution):
        curator.save()
        curator.visible = True
        with pytest.raises(IntegrityError, match='Curators cannot be made bibliographic contributors'):
            curator.save()

        assert curator.visible
        curator.refresh_from_db()
        assert not curator.visible

        # save completes when valid
        curator.visible = False
        curator.save()

    def test_regular_visible_contributor_is_saved(self, user, project):
        contributor = Contributor(
            user=user,
            node=project,
            visible=True,
            is_curator=False
        )
        contributor.save()
        saved_contributor = Contributor.objects.get(pk=contributor.pk)
        assert saved_contributor.user == user
        assert saved_contributor.node == project
        assert saved_contributor.visible is True
        assert saved_contributor.is_curator is False

    def test_invisible_curator_is_saved(self, institutional_admin, curator, project):
        curator.save()
        saved_curator = Contributor.objects.get(pk=curator.pk)
        assert curator == saved_curator
        assert saved_curator.user == institutional_admin
        assert saved_curator.node == project
        assert saved_curator.visible is False
        assert saved_curator.is_curator is True
