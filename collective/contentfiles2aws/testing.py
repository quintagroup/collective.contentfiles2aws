from plone.app.testing import PloneSandboxLayer
from plone.app.testing import PLONE_FIXTURE, PLONE_INTEGRATION_TESTING
from plone.app.testing import IntegrationTesting

from plone.testing import z2
from plone.testing import Layer


class AWSContentFilesFixture(PloneSandboxLayer):

    defaultBases = (PLONE_FIXTURE,)

    def setUpZope(self, app, configurationContext):
        # Load ZCML
        import collective.contentfiles2aws
        self.loadZCML(package=collective.contentfiles2aws)

        z2.installProduct(app, 'collective.contentfiles2aws')


    def setUpPloneSite(self, portal):
        self.applyProfile(portal, 'collective.contentfiles2aws:default')

AWS_CONTENT_FILES_FIXTURE = AWSContentFilesFixture()


class AWSContentFilesUnitTestsFixture(Layer):
    """Unit tests layer for choosehelp.content package"""
    pass

AWS_CONTENT_FILES_UNIT_TESTS_FIXTURE = AWSContentFilesUnitTestsFixture()


class AWSFixture(Layer):
    """ Simple fixture for amazon related tests. """

    def patchS3Connection(self):
        """ Patches S3 connection with mock connection."""

        import boto.s3.connection
        from collective.contentfiles2aws.tests.s3_service_mockup import \
                MockConnection

        boto.s3.connection.S3Connection = MockConnection

        # we need to reload our client module
        # to be able to use patched version.
        import collective.contentfiles2aws.client.awsclient
        reload(collective.contentfiles2aws.client.awsclient)

    def setUp(self):
        """ Sets up amazon fixture. """
        self.patchS3Connection()

AWS_FIXTURE = AWSFixture()

AWS_CONTENT_FILES_INTEGRATION_TESTING = IntegrationTesting(bases=(
    PLONE_INTEGRATION_TESTING, AWS_FIXTURE, AWS_CONTENT_FILES_FIXTURE),
    name="AWSContentFiles:Integration")
