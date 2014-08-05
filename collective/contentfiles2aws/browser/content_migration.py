import transaction
from pprint import pformat
from zope.component import getUtility, queryMultiAdapter
from Products.Five.browser import BrowserView
from Products.CMFCore.utils import getToolByName
from Products.Archetypes.ArchetypeTool import getType
from Products.contentmigration.walker import CustomQueryWalker

from plone.indexer.interfaces import IIndexableObject

from collective.contentfiles2aws.interfaces import IAWSFileClientUtility
from collective.contentfiles2aws.interfaces import IAWSField
from collective.contentfiles2aws.migrations import ATBlobFileToAWSFileMigrator, ATBlobImageToAWSImageMigrator


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
                    #if 'File' in t['name']:
                        #import pdb; pdb.set_trace()
                    if IAWSField.providedBy(f):
                        print t, f
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

class ContentToAWSMigrationView(BrowserView):
    """ Simple browser view for content migration. """
    def stats(self):
        results = {}
        for brain in self.context.portal_catalog():
            results[brain.portal_type] = results.get(brain.portal_type, 0) + 1
        return pformat(sorted(results.items()))

    def __call__(self):
        res = 'State before:\n' + self.stats() + '\n'
        portal = self.context
        for migrator in [ATBlobFileToAWSFileMigrator, ATBlobImageToAWSImageMigrator]:
            walker = CustomQueryWalker(portal, migrator, use_savepoint=True)
            if self.request.get('limit'):
                walker.limit = int(self.request.get('limit'))
            transaction.savepoint(optimistic=True)
            walker.go()
            res += walker.getOutput()
        res += 'State after:\n' + self.stats() + '\n'
        portal.plone_log(res)
        return res

