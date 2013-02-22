import transaction
from zope.component import getUtility, queryMultiAdapter
from Products.Five.browser import BrowserView
from Products.CMFCore.utils import getToolByName
from Products.Archetypes.ArchetypeTool import getType

from plone.indexer.interfaces import IIndexableObject

from collective.contentfiles2aws.interfaces import IAWSFileClientUtility
from collective.contentfiles2aws.interfaces import IAWSField


class ContentMigrationView(BrowserView):
    """ Simple browser view for content migration. """

    bsize = 100

    def get_types(self):
        types_ = []
        pt = getToolByName(self.context, 'portal_types')
        for type_ in pt.listTypeInfo():
            meta_type = type_.Metatype()
            product = type_.product
            try:
                t = getType(meta_type, product)
            except KeyError:
                continue
            if 'schema' in t:
                for f in t['schema'].fields():
                    if IAWSField.providedBy(f):
                        tid = type_.id
                        if tid not in types_:
                            types_.append(tid)
        return types_

    def get_bsize(self):
        bsize = self.request.get('bsize', 0)
        if bsize:
            return int(bsize)
        return self.bsize

    def _update_metadata(self, catalog, obj):
        uid = '/'.join(obj.getPhysicalPath())
        wrapper = queryMultiAdapter((obj, catalog), IIndexableObject)
        catalog._catalog.updateMetadata(wrapper, uid)

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
                    if IAWSField.providedBy(f):
                        name = f.getName()
                        migrate = '%s_migrate' % name
                        obj.REQUEST[migrate] = True
                        f.get(obj)
                        self._update_metadata(pc, obj)
                        count = count + 1
                        if count % self.get_bsize() == 0:
                            transaction.savepoint(optimistic=True)
                        results[ptype] = results[ptype] + 1
        return results

    def __call__(self):
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
                migrated = self._migrate(query, self.get_types())
            else:
                migrated = self._migrate(query, (content_type,))

            if migrated:
                result = '\n'.join(['%s: %d fields migrated' % (k, v)
                                    for k, v in migrated.items()])
        else:
            for ptype in self.get_types():
                query['portal_type'] = ptype
                result += "%s: %d\n" % (ptype, len(pc(**query)))

        return result
