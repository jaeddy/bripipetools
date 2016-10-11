import logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
import os
import re
import datetime

import pytest
import mongomock
from mock import Mock

from bripipetools import model as docs
from bripipetools import genlims


# def test_genlims_connection():
#     # TODO: come up with a better way to test this
#     assert('samples' in genlims.db.collection_names())

@pytest.fixture(scope='function')
def mock_db(request):
    logger.info(("[setup] mock database, connect "
                 "to mock Mongo database"))
    db = mongomock.MongoClient().db
    db.mockcollection.insert(
        {'_id': 'mockobject',
         'type': 'mocked object',
         'updateField': None,
         'skipField': 'mockvalue',
         'arrayField': ['foo', 'bar']}
    )
    def fin():
        logger.info(("[teardown] mock database, disconnect "
                     "from mock Mongo database"))
    request.addfinalizer(fin)
    return db

@pytest.mark.usefixtures('mock_db')
class TestGenLIMSOperations:

    # GIVEN a mocked version of the TG3 Mongo database with example documents
    # for samples, runs, and workflow batches collections
    @pytest.fixture(
        scope='function',
        params=[
            ('dummycollection', {
                'obj_exists': {'target': {'_id': 'foo',
                                          'newField': 'value',
                                          'updateField': 'newvalue',
                                          'skipField': None,
                                          'arrayField': ['foo', 'baz']},
                               'expect_get_len': 0,
                               'expect_put_len': 1,
                               'expect_get_fields': 3,
                               'expect_put_fields': 4},
                'obj_new': {'target': {'_id': 'foo', 'type': 'new_object',
                                       'skipField': None,
                                       'arrayField': ['foo', 'bar']},
                            'expect_get_len': 0,
                            'expect_put_len': 1,
                            'expect_put_fields': 3},
                'objs_new': {'target': [{'_id': 'foo', 'type': 'new_object'},
                                        {'_id': 'bar', 'type': 'new_object'}],
                             'expect_put_len': 2}
            }),
            ('mockcollection', {
                'obj_exists': {'target': {'_id': 'mockobject',
                                          'newField': 'value',
                                          'updateField': 'newvalue',
                                          'skipField': None,
                                          'arrayField': ['foo', 'baz']},
                               'expect_get_len': 1,
                               'expect_put_len': 1,
                               'expect_get_fields': 5,
                               'expect_put_fields': 6},
                'obj_new': {'target': {'_id': 'foo', 'type': 'new_object',
                                       'skipField': None,
                                       'arrayField': ['foo', 'bar']},
                            'expect_get_len': 0,
                            'expect_put_len': 1,
                            'expect_put_fields': 3},
                'objs_new': {'target': [{'_id': 'foo', 'type': 'new_object'},
                                        {'_id': 'bar', 'type': 'new_object'}],
                             'expect_put_len': 2}
            })
        ])
    def testdata(self, request, mock_db):
        logger.info("[setup] test data for collection '{}'"
                    .format(request.param[0]))

        # AND the following scenarios on which to test operations
        logger.info("test object scenarios {}"
                    .format(request.param[1]))
        def fin():
            logger.info("[teardown] test data for collection '{}', "
                        "drop collection"
                        .format(request.param[0]))
            mock_db[request.param[0]].drop()
        request.addfinalizer(fin)
        return request.param

    def test_find_objects_that_are_new(self, mock_db, testdata):
        # AND the target object does not exist in the database
        logger.info("test `find_objects()` when objects do not exist")

        test_collection, test_object = testdata[0], testdata[1]['obj_new']

        # WHEN querying for the object
        mock_fn = Mock(name='mock_fn',
                       return_value=(mock_db,
                                     {'_id': test_object['target']['_id']}))
        mock_fn.__name__ = 'mock_fn'
        wrapped_fn = genlims.find_objects(test_collection)(mock_fn)
        objects = wrapped_fn()

        # THEN should return an empty list
        assert(len(objects) == test_object['expect_get_len'])

    def test_find_objects_that_exist(self, mock_db, testdata):
        # AND the target object exists in the database
        logger.info("test `find_objects()` when objects exist")

        test_collection, test_object = testdata[0], testdata[1]['obj_exists']

        # WHEN querying for the object
        mock_fn = Mock(name='mock_fn',
                       return_value=(mock_db,
                                     {'_id': test_object['target']['_id']}))
        mock_fn.__name__ = 'mock_fn'
        wrapped_fn = genlims.find_objects(test_collection)(mock_fn)
        objects = wrapped_fn()

        # THEN should return a non-empty list of length 1 and object
        # should have expected number of fields
        assert(len(objects) == test_object['expect_get_len'])
        if len(objects):
            assert(len(objects[0]) == test_object['expect_get_fields'])

    def test_insert_objects_one_new(self, mock_db, testdata):
        # AND the target object does not exist in the database
        logger.info("test `insert_objects()` with one new object")

        test_collection, test_object = testdata[0], testdata[1]['obj_new']

        # WHEN inserting the object
        mock_fn = Mock(name='mock_fn',
                       return_value=(mock_db, test_object['target']))
        mock_fn.__name__ = 'mock_fn'
        wrapped_fn = genlims.insert_objects(test_collection)(mock_fn)
        wrapped_fn()
        new_object = (mock_db[test_collection]
                      .find_one({'_id': test_object['target']['_id']}))

        # THEN new object should be in database, should have the expected
        # number of fields, should not include the empty (skipped) field from
        # the input object, and the array field should be a list
        assert(len(list(mock_db[test_collection].find({'type': 'new_object'})))
               == test_object['expect_put_len'])
        assert(len(new_object) == test_object['expect_put_fields'])
        assert('skipField' not in new_object)
        assert(isinstance(new_object['arrayField'], list))

    def test_insert_objects_multiple_new(self, mock_db, testdata):
        # AND the target objects does not exist in the database
        logger.info("test `insert_objects()` with multiple new objects")

        test_collection, test_object = testdata[0], testdata[1]['objs_new']

        # WHEN inserting the object
        mock_fn = Mock(name='mock_fn',
                       return_value=(mock_db, test_object['target']))
        mock_fn.__name__ = 'mock_fn'
        wrapped_fn = genlims.insert_objects(test_collection)(mock_fn)
        wrapped_fn()

        # THEN new objects should be in database
        assert(len(list(mock_db[test_collection].find({'type': 'new_object'})))
               == test_object['expect_put_len'])

    def test_insert_objects_one_that_exists(self, mock_db, testdata):
        # AND the target object exists in the database
        logger.info("test `insert_objects()` with one object that exists")

        test_collection, test_object = testdata[0], testdata[1]['obj_exists']

        # WHEN inserting the object
        mock_fn = Mock(name='mock_fn',
                       return_value=(mock_db, test_object['target']))
        mock_fn.__name__ = 'mock_fn'
        wrapped_fn = genlims.insert_objects(test_collection)(mock_fn)
        wrapped_fn()
        updated_object = (mock_db[test_collection]
                          .find_one({'_id': test_object['target']['_id']}))

        # THEN new object should be in database, should have the expected
        # number of fields, should have the original value for the skipped
        # field, should have the updated value for the update field, and
        # should have updated values in the array field
        assert(len(list(mock_db[test_collection]
                        .find({'_id': test_object['target']['_id']})))
               == test_object['expect_put_len'])
        assert(len(updated_object) == test_object['expect_put_fields'])
        if 'skipField' in updated_object:
            assert(updated_object['skipField'] is not None)
        assert(updated_object['updateField'] is not None)
        assert('baz' in updated_object['arrayField'])

    # GIVEN wrapped get/put functions for specific collections
    @pytest.fixture(
        scope='function',
        params=[
            ('samples', {'get_fn': genlims.get_samples,
                         'put_fn': genlims.put_samples}),
            ('runs', {'get_fn': genlims.get_runs,
                      'put_fn': genlims.put_runs}),
            ('workflowbatches', {'get_fn': genlims.get_workflowbatches,
                                 'put_fn': genlims.put_workflowbatches}),
        ])
    def wrappedfndata(self, request, mock_db):
        # AND a minimal object present in the collection
        logger.info("[setup] test data & wrapped functions for collection '{}'"
                    .format(request.param[0]))
        mock_db[request.param[0]].insert({'_id': 'mockobject'})

        def fin():
            logger.info("[teardown] test data for collection '{}', "
                        "drop collection"
                        .format(request.param[0]))
            mock_db[request.param[0]].drop()
        request.addfinalizer(fin)
        return request.param

    def test_wrapped_get_functions(self, mock_db, wrappedfndata):
        logger.info("test `get_{}()`".format(wrappedfndata[0]))

        # WHEN inserting new object(s)
        objects = wrappedfndata[1]['get_fn'](mock_db, {'_id': 'mockobject'})

        # THEN should be list of length 1
        assert(len(objects) == 1)

    def test_wrapped_put_functions(self, mock_db, wrappedfndata):
        logger.info("test `get_{}()`".format(wrappedfndata[0]))

        # WHEN inserting new object(s)
        wrappedfndata[1]['put_fn'](mock_db, {'_id': 'new_object'})

        # THEN should be list of length 1
        assert(len(list(mock_db[wrappedfndata[0]].find()))
               == 2)

    def test_create_workflowbatch_id_new(self, mock_db):
        # GIVEN a prefix/date combination that does not yet exist in
        # the database
        logger.info("test `create_workflowbatch_id()`, new prefix/date")

        # WHEN creating new workflow batch ID
        wb_id = genlims.create_workflowbatch_id(
            db=mock_db,
            prefix='mockprefix',
            date=datetime.datetime(2000, 1, 1, 0, 0))

        # THEN constructed workflow batch ID should end in number 1
        assert(wb_id == 'mockprefix_2000-01-01_1')

    def test_create_workflowbatch_id_existing(self, mock_db):
        # GIVEN a prefix/date combination that already exists in
        # the database
        logger.info("test `create_workflowbatch_id()`, existing prefix/date")

        mock_db.workflowbatches.insert(
            {'_id': 'mockprefix_2000-01-01_1',
             'date': datetime.datetime(2000, 1, 1, 0, 0)})

        # WHEN creating new workflow batch ID
        wb_id = genlims.create_workflowbatch_id(
            db=mock_db,
            prefix='mockprefix',
            date=datetime.datetime(2000, 1, 1, 0, 0))

        # THEN constructed workflow batch ID should end in number 2
        assert(wb_id == 'mockprefix_2000-01-01_2')

    def test_search_ancestors_field_in_sample(self, mock_db):
        # GIVEN an existing sample with a field that matches the input
        # argument
        logger.info("test `search_ancestors()`, sample has field")

        mock_db.samples.insert(
            {'_id': 'mocksample',
             'parentId': 'mockparent',
             'mockfield': 'mockvalue'})

        # WHEN searching for the field among all sample ancestors
        value = genlims.search_ancestors(mock_db, 'mocksample', 'mockfield')

        # THEN should return the value of the field from the first sample
        # checked
        assert(value == 'mockvalue')

    def test_search_ancestors_field_in_parent(self, mock_db):
        # GIVEN an existing sample with a parent sample that includes the
        # input field
        logger.info("test `search_ancestors()`, parent has field")

        mock_db.samples.insert(
            {'_id': 'mocksample',
             'parentId': 'mockparent'})
        mock_db.samples.insert(
            {'_id': 'mockparent',
             'mockfield': 'mockvalue'})

        # WHEN searching for the field among all sample ancestors
        value = genlims.search_ancestors(mock_db, 'mocksample', 'mockfield')

        # THEN should return the value of the field from the parent sample
        assert(value == 'mockvalue')

    def test_search_ancestors_field_in_grandparent(self, mock_db):
        # GIVEN an existing sample with a grandparent sample (parent of a
        # parent) that includes the input field
        logger.info("test `search_ancestors()`, grandparent has field")

        mock_db.samples.insert(
            {'_id': 'mocksample',
             'parentId': 'mockparent'})
        mock_db.samples.insert(
            {'_id': 'mockparent',
             'parentId': 'mockgrandparent'})
        mock_db.samples.insert(
            {'_id': 'mockgrandparent',
             'mockfield': 'mockvalue'})

        # WHEN searching for the field among all sample ancestors
        value = genlims.search_ancestors(mock_db, 'mocksample', 'mockfield')

        # THEN should return the value of the field from the parent sample
        assert(value == 'mockvalue')

    def test_search_ancestors_no_parent(self, mock_db):
        # GIVEN an existing sample with that has no 'parentId' field
        logger.info("test `search_ancestors()`, no parent indicated")

        mock_db.samples.insert(
            {'_id': 'mocksample'})
        mock_db.samples.insert(
            {'_id': 'mockparent',
             'mockfield': 'mockvalue'})

        # WHEN searching for the field among all sample ancestors
        value = genlims.search_ancestors(mock_db, 'mocksample', 'mockfield')

        # THEN should return None
        assert(value is None)

    def test_search_ancestors_no_field(self, mock_db):
        # GIVEN an existing sample with no ancestors that include the
        # input field
        logger.info("test `search_ancestors()`, no parent indicated")

        mock_db.samples.insert(
            {'_id': 'mocksample',
             'parentId': 'mockparent'})
        mock_db.samples.insert(
            {'_id': 'mockparent'})

        # WHEN searching for the field among all sample ancestors
        value = genlims.search_ancestors(mock_db, 'mocksample', 'mockfield')

        # THEN should return None
        assert(value is None)


class TestMapping:
    # GIVEN any state

    def test_map_keys(self):
        logger.info("test `map_keys()`")

        # WHEN formatting camel-case keys/fields in an object

        # THEN keys at all nested levels should be converted to snake case
        # (with the exception of '_id', which should be unchangedj)
        assert(genlims.map_keys({'aB': None}) == {'a_b': None})
        assert(genlims.map_keys({'aB': [{'bC': None}]}) ==
            {'a_b': [{'b_c': None}]})
        assert(genlims.map_keys({'_id': None}) == {'_id': None})

    def test_get_model_class(self):
        logger.info("test `_get_model_class()`")

        # WHEN searching for matched model class based on object type

        # THEN should return expected class name
        assert(genlims.get_model_class({'type': 'sequenced library'})
               == 'SequencedLibrary')
        assert(genlims.get_model_class({'type': 'library'})
               == 'Library')

    def test_map_to_object(self):
        logger.info("test `map_to_object()`")

        # WHEN mapping a database object to a class instance
        doc = {'_id': 'lib7293_C6VG0ANXX',
               'parentId': 'lib7293',
               'type': 'sequenced library',
               'rawData': [{'path': None,
                            'laneId': 'L001',
                            'sampleNumber': 1}]}
        obj = genlims.map_to_object(doc)

        # THEN the model class instance should be the correct type and
        # include the appropriately formatted fields/attributes
        # TODO: try to remove dependency on model/docs module when testing,
        # if possible (and maybe even in the method itself)
        assert(type(obj) is docs.SequencedLibrary)
        assert(all([hasattr(obj, field)
                    for field in ['_id', 'parent_id', 'type', 'raw_data',
                                  'date_created', 'last_updated']]))
        assert(all([field in obj.raw_data]
                    for field in ['path', 'lane_id', 'sample_number']))
        assert(obj.last_updated == obj.date_created)
