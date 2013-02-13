import transaction
from zope.component import getUtility
from Products.Five.browser import BrowserView
from Products.CMFCore.utils import getToolByName

from collective.contentfiles2aws.interfaces import IAWSFileClientUtility

MTYPES = ('CHArticle', 'CHNewsArticle', 'CHNewsFile', 'CHNewsImage',
          'CHPlainPromoPage', 'CHProgramPromoPage', 'CHPromoImage',
          'CHPromoPage', 'CHSponsorAd', 'CHTopic', 'CHTopicImage')


class ContentMigrationView(BrowserView):
    """ Simple browser view for content migration. """

    bsize = 100

    def get_bsize(self):
        bsize = self.request.get('bsize', 0)
        if bsize:
            return int(bsize)
        return self.bsize

    def _migrate(self, query, types):
        count = 0
        results = {}
        pc = getToolByName(self.context, 'portal_catalog')

        for ptype in types:
            query['portal_type'] = ptype
            results[ptype] = 0
            for b in pc(**query):
                obj = b.getObject()
                for f in obj.schema.fields():
                    if f.type in ('file', 'image'):
                        name = f.getName()
                        migrate = '%s_migrate' % name
                        obj.REQUEST[migrate] = True
                        f.get(obj)
                        count = count + 1
                        if count % self.get_bsize() == 0:
                            transaction.savepoint(optimistic=True)
                        results[ptype] = results[ptype] + 1
        return results

    def __call__(self):
        """
        """
        aws_utility = getUtility(IAWSFileClientUtility)
        if not aws_utility.active():
            return "AWSStorage isn't active. Nothing to do!"

        result = ''
        pc = getToolByName(self.context, 'portal_catalog')
        query = {'path': {'query': '/'.join(self.context.getPhysicalPath())}}
        content_type = self.request.get('content_type', '')
        migrated = None
        if content_type:
            if content_type.lower() == 'all':
                migrated = self._migrate(query, MTYPES)
            else:
                migrated = self._migrate(query, (content_type,))

            if migrated:
                result = '\n'.join(['%s: %d fields migrated' % (k, v)
                                    for k, v in migrated.items()])
        else:
            for ptype in MTYPES:
                query['portal_type'] = ptype
                result += "%s: %d\n" % (ptype, len(pc(**query)))

        return result
