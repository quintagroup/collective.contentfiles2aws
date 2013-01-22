from types import FileType

from AccessControl import ClassSecurityInfo

from Products.Archetypes.atapi import FileWidget
from Products.Archetypes.Registry import registerWidget

class AWSFileWidget(FileWidget):
    _properties = FileWidget._properties.copy()
    _properties.update({
        'macro' : "awsfile",
        })

    def href(self, instance, field):
        return field.url(instance)

registerWidget(AWSFileWidget,
               title='AWS File',
               description='Renders a HTML widget upload a file',
               used_for=('collective.contentfiles2aws.fields.AWSFileField',)
               )

class AWSImageWidget(AWSFileWidget):
    _properties = FileWidget._properties.copy()
    _properties.update({
        'macro' : "awsimage",
        # only display if size <= threshold, otherwise show link
        'display_threshold': 102400,
        # use this scale for the preview in the edit form, default to 'preview'
        # if this scale isn't available then use the display_threshold
        'preview_scale': 'preview',
        })

    security = ClassSecurityInfo()

    security.declarePublic('process_form')
    def process_form(self, instance, field, form, empty_marker=None,
                     emptyReturnsMarker=False, validating=True):
        """form processing that deals with image data (and its delete case)"""
        value = None
        ## check to see if the delete hidden was selected
        delete = form.get('%s_delete' % field.getName(), empty_marker)
        if delete=='delete': return "DELETE_IMAGE", {}
        if delete=='nochange' : return empty_marker


        fileobj = form.get('%s_file' % field.getName(), empty_marker)

        if fileobj is empty_marker: return empty_marker

        filename = getattr(fileobj, 'filename', '') or \
                   (isinstance(fileobj, FileType) and \
                    getattr(fileobj, 'name', ''))

        if filename:
            value = fileobj

        if not value: return None
        return value, {}

    security.declarePublic('preview_tag')
    def preview_tag(self, instance, field):
        """Return a tag for a preview image, or None if no preview is found."""
        img=field.get(instance)
        if not img:
            return None

        if self.preview_scale in field.sizes:
            return field.tag(instance, scale=self.preview_scale)

        if img.getSize()<=self.display_threshold:
            return field.tag(instance)

        return None

registerWidget(AWSImageWidget,
               title='AWS Image',
               description=('Renders a HTML widget for '
                            'uploading/displaying an image'),
               used_for=('collective.contentfiles2aws.fields.AWSImageField',)
               )
