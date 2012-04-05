# -*- coding: utf-8; Mode: Python -*-
#
# Copyright 2012 Jeffrey Finkelstein <jeffrey.finkelstein@gmail.com>
#
# This file is part of Flask-Restless.
#
# Flask-Restless is free software: you can redistribute it and/or modify it
# under the terms of the GNU Affero General Public License as published by the
# Free Software Foundation, either version 3 of the License, or (at your
# option) any later version.
#
# Flask-Restless is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License
# along with Flask-Restless. If not, see <http://www.gnu.org/licenses/>.
"""Unit tests for the :mod:`flask_restless.search` module."""
from __future__ import with_statement

from unittest2 import TestSuite
from unittest2 import TestCase

from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.orm.exc import NoResultFound

from flask.ext.restless.search import create_query
from flask.ext.restless.search import Filter
from flask.ext.restless.search import search
from flask.ext.restless.search import SearchParameters

from .helpers import TestSupportPrefilled


__all__ = ['OperatorsTest', 'QueryCreationTest', 'SearchTest']


class QueryCreationTest(TestSupportPrefilled):
    """Unit tests for the :func:`flask_restless.search.create_query`
    function.

    """

    def test_empty_search(self):
        """Tests that a query with no search parameters returns everything."""
        query = create_query(self.db.session, self.Person, {})
        self.assertEqual(query.all(), self.people)

    def test_dict_same_as_search_params(self):
        """Tests that creating a query using a dictionary results in the same
        query as creating one using a
        :class:`flask_restless.search.SearchParameters` object.

        """
        d = {'filters': [{'name': 'name', 'val': u'%y%', 'op': 'like'}]}
        s = SearchParameters.from_dictionary(d)
        query_d = create_query(self.db.session, self.Person, d)
        query_s = create_query(self.db.session, self.Person, s)
        self.assertEqual(query_d.all(), query_s.all())

    def test_basic_query(self):
        """Tests for basic query correctness."""
        d = {'filters': [{'name': 'name', 'val': u'%y%', 'op': 'like'}]}
        query = create_query(self.db.session, self.Person, d)
        self.assertEqual(query.count(), 3)  # Mary, Lucy and Katy

        d = {'filters': [{'name': 'name', 'val': u'Lincoln', 'op': 'equals'}]}
        query = create_query(self.db.session, self.Person, d)
        self.assertEqual(query.count(), 1)
        self.assertEqual(query.one().name, 'Lincoln')

        d = {'filters': [{'name': 'name', 'val': u'Bogus', 'op': 'equals'}]}
        query = create_query(self.db.session, self.Person, d)
        self.assertEqual(query.count(), 0)

        d = {'order_by': [{'field': 'age', 'direction': 'asc'}]}
        query = create_query(self.db.session, self.Person, d)
        ages = [p.age for p in query]
        self.assertEqual(ages, [7, 19, 23, 25, 28])

        d = {'filters': [{'name': 'age', 'val': [7, 28], 'op': 'in'}]}
        query = create_query(self.db.session, self.Person, d)
        ages = [p.age for p in query]
        self.assertEqual(ages, [7, 28])

    def test_query_related_field(self):
        """Test for making a query with respect to a related field."""
        # add a computer to person 1
        computer = self.Computer(name=u'turing', vendor=u'Dell')
        p1 = self.Person.query.get(1)
        p1.computers.append(computer)
        self.db.session.commit()

        d = {'filters': [{'name': 'computers__name', 'val': u'turing',
                          'op': 'any'}]}
        query = create_query(self.db.session, self.Person, d)
        self.assertEqual(query.count(), 1)
        self.assertEqual(query.one().computers[0].name, 'turing')

        d = {'filters': [{'name': 'age', 'op': 'lte', 'field': 'other'}],
            'order_by': [{'field': 'other'}]}
        query = create_query(self.db.session, self.Person, d)
        self.assertEqual(query.count(), 2)
        results = query.all()
        self.assertEqual(results[0].other, 10)
        self.assertEqual(results[1].other, 19)


class OperatorsTest(TestSupportPrefilled):
    """Tests for each of the query operators defined in
    :data:`flask_restless.search.OPERATORS`.

    """

    def test_operators(self):
        for op in '==', 'eq', 'equals', 'equal_to':
            d = dict(filters=[dict(name='name', op=op, val='Lincoln')])
            result = search(self.db.session, self.Person, d)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0].name, 'Lincoln')
        for op in '!=', 'ne', 'neq', 'not_equal_to', 'does_not_equal':
            d = dict(filters=[dict(name='name', op=op, val='Lincoln')])
            result = search(self.db.session, self.Person, d)
            self.assertEqual(len(result), len(self.people) - 1)
            self.assertNotIn('Lincoln', (p.name for p in result))
        for op in '>', 'gt':
            d = dict(filters=[dict(name='age', op=op, val=20)])
            result = search(self.db.session, self.Person, d)
            self.assertEqual(len(result), 3)
        for op in '<', 'lt':
            d = dict(filters=[dict(name='age', op=op, val=20)])
            result = search(self.db.session, self.Person, d)
            self.assertEqual(len(result), 2)
        for op in '>=', 'ge', 'gte', 'geq':
            d = dict(filters=[dict(name='age', op=op, val=23)])
            result = search(self.db.session, self.Person, d)
            self.assertEqual(len(result), 3)
        for op in '<=', 'le', 'lte', 'leq':
            d = dict(filters=[dict(name='age', op=op, val=23)])
            result = search(self.db.session, self.Person, d)
            self.assertEqual(len(result), 3)
        d = dict(filters=[dict(name='name', op='like', val='%y%')])
        result = search(self.db.session, self.Person, d)
        self.assertEqual(len(result), 3)
        d = dict(filters=[dict(name='age', op='in', val=[19, 21, 23])])
        result = search(self.db.session, self.Person, d)
        self.assertEqual(len(result), 2)
        d = dict(filters=[dict(name='age', op='not_in', val=[19, 21, 23])])
        result = search(self.db.session, self.Person, d)
        self.assertEqual(len(result), 3)
        d = dict(filters=[dict(name='birth_date', op='is_null')])
        result = search(self.db.session, self.Person, d)
        self.assertEqual(len(result), 4)
        d = dict(filters=[dict(name='birth_date', op='is_not_null')])
        result = search(self.db.session, self.Person, d)
        self.assertEqual(len(result), 1)
        # desc
        # asc
        # has
        # any


class SearchTest(TestSupportPrefilled):
    """Unit tests for the :func:`flask_restless.search.search` function.

    The :func:`~flask_restless.search.search` function is a essentially a
    wrapper around the :func:`~flask_restless.search.create_query` function
    which checks whether the parameters of the search indicate that a single
    result is expected.

    """

    def test_search(self):
        """Tests that asking for a single result raises an error unless the
        result of the query truly has only a single element.

        """
        # tests getting multiple results
        d = {'single': True,
             'filters': [{'name': 'name', 'val': u'%y%', 'op': 'like'}]}
        with self.assertRaises(MultipleResultsFound):
            search(self.db.session, self.Person, d)

        # tests getting no results
        d = {'single': True,
             'filters': [{'name': 'name', 'val': u'bogusname', 'op': '=='}]}
        with self.assertRaises(NoResultFound):
            search(self.db.session, self.Person, d)

        # tests getting exactly one result
        d = {'single': True,
             'filters': [{'name': 'name', 'val': u'Lincoln', 'op': '=='}]}
        result = search(self.db.session, self.Person, d)
        self.assertEqual(result.name, u'Lincoln')


def load_tests(loader, standard_tests, pattern):
    """Returns the test suite for this module."""
    suite = TestSuite()
    suite.addTest(loader.loadTestsFromTestCase(OperatorsTest))
    suite.addTest(loader.loadTestsFromTestCase(QueryCreationTest))
    suite.addTest(loader.loadTestsFromTestCase(SearchTest))
    return suite
