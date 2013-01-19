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
