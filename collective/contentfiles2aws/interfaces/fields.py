from zope.interface import Interface

class IAWSField(Interface):
    """ Base interface for aws related fields."""

class IAWSFileField(IAWSField):
    """ Marker interface for AWSFileField """

class IAWSImageField(IAWSField):
    """ Marker interface for AWSImageField """

