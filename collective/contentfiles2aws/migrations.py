from OFS.Image import File
from Products.contentmigration.archetypes import InplaceATItemMigrator as BaseMigrator
from plone.app.blob.interfaces import IATBlobFile
from plone.app.blob.interfaces import IATBlobImage
from zope.interface import noLongerProvides


class ATBlobFileToAWSFileMigrator(BaseMigrator):
    src_portal_type = 'File'
    src_meta_type = 'ATBlob'
    dst_portal_type = 'AWSFile'
    dst_meta_type = 'AWSFile'

    # migrate all fields except 'file', which needs special handling...
    fields_map = {
        'file': None,
    }

    def migrate_data(self):
        value = self.old.getField('file').getAccessor(self.old)()
        self.new.getField('file').getMutator(self.new)(File(value.filename, '', value.data, value.content_type))

    def finalize(self):
        BaseMigrator.finalize(self)
        noLongerProvides(self.new, IATBlobFile)


class ATBlobImageToAWSImageMigrator(BaseMigrator):
    src_portal_type = 'Image'
    src_meta_type = 'ATBlob'
    dst_portal_type = 'AWSImage'
    dst_meta_type = 'AWSImage'

    # migrate all fields except 'image', which needs special handling...
    fields_map = {
        'image': None,
    }

    def migrate_data(self):
        value = self.old.getField('image').getAccessor(self.old)()
        self.new.getField('image').getMutator(self.new)(File(value.filename, '', value.data, value.content_type))

    def finalize(self):
        BaseMigrator.finalize(self)
        noLongerProvides(self.new, IATBlobImage)
