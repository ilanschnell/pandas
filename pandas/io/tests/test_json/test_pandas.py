# pylint: disable-msg=W0612,E1101
from pandas.compat import range, lrange, StringIO
from pandas import compat
import os

import numpy as np

from pandas import Series, DataFrame, DatetimeIndex, Timestamp
import pandas as pd
read_json = pd.read_json

from pandas.util.testing import (assert_almost_equal, assert_frame_equal,
                                 assert_series_equal, network,
                                 ensure_clean, assert_index_equal)
import pandas.util.testing as tm

_seriesd = tm.getSeriesData()
_tsd = tm.getTimeSeriesData()

_frame = DataFrame(_seriesd)
_frame2 = DataFrame(_seriesd, columns=['D', 'C', 'B', 'A'])
_intframe = DataFrame(dict((k, v.astype(np.int64))
                           for k, v in compat.iteritems(_seriesd)))

_tsframe = DataFrame(_tsd)

_mixed_frame = _frame.copy()

class TestPandasContainer(tm.TestCase):

    def setUp(self):
        self.dirpath = tm.get_data_path()

        self.ts = tm.makeTimeSeries()
        self.ts.name = 'ts'

        self.series = tm.makeStringSeries()
        self.series.name = 'series'

        self.objSeries = tm.makeObjectSeries()
        self.objSeries.name = 'objects'

        self.empty_series = Series([], index=[])
        self.empty_frame = DataFrame({})

        self.frame = _frame.copy()
        self.frame2 = _frame2.copy()
        self.intframe = _intframe.copy()
        self.tsframe = _tsframe.copy()
        self.mixed_frame = _mixed_frame.copy()

    def tearDown(self):
        del self.dirpath

        del self.ts

        del self.series

        del self.objSeries

        del self.empty_series
        del self.empty_frame

        del self.frame
        del self.frame2
        del self.intframe
        del self.tsframe
        del self.mixed_frame

    def test_frame_double_encoded_labels(self):
        df = DataFrame([['a', 'b'], ['c', 'd']],
                       index=['index " 1', 'index / 2'],
                       columns=['a \\ b', 'y / z'])

        assert_frame_equal(df, read_json(df.to_json(orient='split'),
                                         orient='split'))
        assert_frame_equal(df, read_json(df.to_json(orient='columns'),
                                         orient='columns'))
        assert_frame_equal(df, read_json(df.to_json(orient='index'),
                                         orient='index'))
        df_unser = read_json(df.to_json(orient='records'), orient='records')
        assert_index_equal(df.columns, df_unser.columns)
        np.testing.assert_equal(df.values, df_unser.values)

    def test_frame_non_unique_index(self):
        df = DataFrame([['a', 'b'], ['c', 'd']], index=[1, 1],
                       columns=['x', 'y'])

        self.assertRaises(ValueError, df.to_json, orient='index')
        self.assertRaises(ValueError, df.to_json, orient='columns')

        assert_frame_equal(df, read_json(df.to_json(orient='split'),
                                         orient='split'))
        unser = read_json(df.to_json(orient='records'), orient='records')
        self.assertTrue(df.columns.equals(unser.columns))
        np.testing.assert_equal(df.values, unser.values)
        unser = read_json(df.to_json(orient='values'), orient='values')
        np.testing.assert_equal(df.values, unser.values)

    def test_frame_non_unique_columns(self):
        df = DataFrame([['a', 'b'], ['c', 'd']], index=[1, 2],
                       columns=['x', 'x'])

        self.assertRaises(ValueError, df.to_json, orient='index')
        self.assertRaises(ValueError, df.to_json, orient='columns')
        self.assertRaises(ValueError, df.to_json, orient='records')

        assert_frame_equal(df, read_json(df.to_json(orient='split'),
                                         orient='split', dtype=False))
        unser = read_json(df.to_json(orient='values'), orient='values')
        np.testing.assert_equal(df.values, unser.values)

        # GH4377; duplicate columns not processing correctly
        df = DataFrame([['a','b'],['c','d']], index=[1,2], columns=['x','y'])
        result = read_json(df.to_json(orient='split'), orient='split')
        assert_frame_equal(result, df)

        def _check(df):
            result = read_json(df.to_json(orient='split'), orient='split',
                               convert_dates=['x'])
            assert_frame_equal(result, df)

        for o in [[['a','b'],['c','d']],
                  [[1.5,2.5],[3.5,4.5]],
                  [[1,2.5],[3,4.5]],
                  [[Timestamp('20130101'),3.5],[Timestamp('20130102'),4.5]]]:
            _check(DataFrame(o, index=[1,2], columns=['x','x']))

    def test_frame_from_json_to_json(self):
        def _check_orient(df, orient, dtype=None, numpy=False,
                          convert_axes=True, check_dtype=True, raise_ok=None):
            df = df.sort()
            dfjson = df.to_json(orient=orient)

            try:
                unser = read_json(dfjson, orient=orient, dtype=dtype,
                                  numpy=numpy, convert_axes=convert_axes)
            except Exception as detail:
                if raise_ok is not None:
                    if isinstance(detail, raise_ok):
                        return
                    raise

            unser = unser.sort()

            if dtype is False:
                check_dtype=False

            if not convert_axes and df.index.dtype.type == np.datetime64:
                unser.index = DatetimeIndex(
                    unser.index.values.astype('i8') * 1e6)
            if orient == "records":
                # index is not captured in this orientation
                assert_almost_equal(df.values, unser.values)
                self.assertTrue(df.columns.equals(unser.columns))
            elif orient == "values":
                # index and cols are not captured in this orientation
                assert_almost_equal(df.values, unser.values)
            elif orient == "split":
                # index and col labels might not be strings
                unser.index = [str(i) for i in unser.index]
                unser.columns = [str(i) for i in unser.columns]
                unser = unser.sort()
                assert_almost_equal(df.values, unser.values)
            else:
                if convert_axes:
                    assert_frame_equal(df, unser, check_dtype=check_dtype)
                else:
                    assert_frame_equal(df, unser, check_less_precise=False,
                                       check_dtype=check_dtype)

        def _check_all_orients(df, dtype=None, convert_axes=True, raise_ok=None):

            # numpy=False
            if convert_axes:
                _check_orient(df, "columns", dtype=dtype)
                _check_orient(df, "records", dtype=dtype)
                _check_orient(df, "split", dtype=dtype)
                _check_orient(df, "index", dtype=dtype)
                _check_orient(df, "values", dtype=dtype)

            _check_orient(df, "columns", dtype=dtype, convert_axes=False)
            _check_orient(df, "records", dtype=dtype, convert_axes=False)
            _check_orient(df, "split", dtype=dtype, convert_axes=False)
            _check_orient(df, "index", dtype=dtype, convert_axes=False)
            _check_orient(df, "values", dtype=dtype ,convert_axes=False)

            # numpy=True and raise_ok might be not None, so ignore the error
            if convert_axes:
                _check_orient(df, "columns", dtype=dtype, numpy=True,
                              raise_ok=raise_ok)
                _check_orient(df, "records", dtype=dtype, numpy=True,
                              raise_ok=raise_ok)
                _check_orient(df, "split", dtype=dtype, numpy=True,
                              raise_ok=raise_ok)
                _check_orient(df, "index", dtype=dtype, numpy=True,
                              raise_ok=raise_ok)
                _check_orient(df, "values", dtype=dtype, numpy=True,
                              raise_ok=raise_ok)

            _check_orient(df, "columns", dtype=dtype, numpy=True,
                          convert_axes=False, raise_ok=raise_ok)
            _check_orient(df, "records", dtype=dtype, numpy=True,
                          convert_axes=False, raise_ok=raise_ok)
            _check_orient(df, "split", dtype=dtype, numpy=True,
                          convert_axes=False, raise_ok=raise_ok)
            _check_orient(df, "index", dtype=dtype, numpy=True,
                          convert_axes=False, raise_ok=raise_ok)
            _check_orient(df, "values", dtype=dtype, numpy=True,
                          convert_axes=False, raise_ok=raise_ok)

        # basic
        _check_all_orients(self.frame)
        self.assertEqual(self.frame.to_json(),
                         self.frame.to_json(orient="columns"))

        _check_all_orients(self.intframe, dtype=self.intframe.values.dtype)
        _check_all_orients(self.intframe, dtype=False)

        # big one
        # index and columns are strings as all unserialised JSON object keys
        # are assumed to be strings
        biggie = DataFrame(np.zeros((200, 4)),
                           columns=[str(i) for i in range(4)],
                           index=[str(i) for i in range(200)])
        _check_all_orients(biggie,dtype=False,convert_axes=False)

        # dtypes
        _check_all_orients(DataFrame(biggie, dtype=np.float64),
                           dtype=np.float64, convert_axes=False)
        _check_all_orients(DataFrame(biggie, dtype=np.int), dtype=np.int,
                           convert_axes=False)
        _check_all_orients(DataFrame(biggie, dtype='U3'), dtype='U3',
                           convert_axes=False, raise_ok=ValueError)

        # empty
        _check_all_orients(self.empty_frame)

        # time series data
        _check_all_orients(self.tsframe)

        # mixed data
        index = pd.Index(['a', 'b', 'c', 'd', 'e'])
        data = {
            'A': [0., 1., 2., 3., 4.],
            'B': [0., 1., 0., 1., 0.],
            'C': ['foo1', 'foo2', 'foo3', 'foo4', 'foo5'],
            'D': [True, False, True, False, True]
        }
        df = DataFrame(data=data, index=index)
        _check_orient(df, "split", check_dtype=False)
        _check_orient(df, "records", check_dtype=False)
        _check_orient(df, "values", check_dtype=False)
        _check_orient(df, "columns", check_dtype=False)
        # index oriented is problematic as it is read back in in a transposed
        # state, so the columns are interpreted as having mixed data and
        # given object dtypes.
        # force everything to have object dtype beforehand
        _check_orient(df.transpose().transpose(), "index", dtype=False)

    def test_frame_from_json_bad_data(self):
        self.assertRaises(ValueError, read_json, StringIO('{"key":b:a:d}'))

        # too few indices
        json = StringIO('{"columns":["A","B"],'
                        '"index":["2","3"],'
                        '"data":[[1.0,"1"],[2.0,"2"],[null,"3"]]}')
        self.assertRaises(ValueError, read_json, json,
                          orient="split")

        # too many columns
        json = StringIO('{"columns":["A","B","C"],'
                        '"index":["1","2","3"],'
                        '"data":[[1.0,"1"],[2.0,"2"],[null,"3"]]}')
        self.assertRaises(AssertionError, read_json, json,
                          orient="split")

        # bad key
        json = StringIO('{"badkey":["A","B"],'
                        '"index":["2","3"],'
                        '"data":[[1.0,"1"],[2.0,"2"],[null,"3"]]}')
        with tm.assertRaisesRegexp(ValueError, r"unexpected key\(s\): badkey"):
            read_json(json, orient="split")

    def test_frame_from_json_nones(self):
        df = DataFrame([[1, 2], [4, 5, 6]])
        unser = read_json(df.to_json())
        self.assertTrue(np.isnan(unser[2][0]))

        df = DataFrame([['1', '2'], ['4', '5', '6']])
        unser = read_json(df.to_json())
        self.assertTrue(np.isnan(unser[2][0]))
        unser = read_json(df.to_json(),dtype=False)
        self.assertTrue(unser[2][0] is None)
        unser = read_json(df.to_json(),convert_axes=False,dtype=False)
        self.assertTrue(unser['2']['0'] is None)

        unser = read_json(df.to_json(), numpy=False)
        self.assertTrue(np.isnan(unser[2][0]))
        unser = read_json(df.to_json(), numpy=False, dtype=False)
        self.assertTrue(unser[2][0] is None)
        unser = read_json(df.to_json(), numpy=False, convert_axes=False, dtype=False)
        self.assertTrue(unser['2']['0'] is None)

        # infinities get mapped to nulls which get mapped to NaNs during
        # deserialisation
        df = DataFrame([[1, 2], [4, 5, 6]])
        df[2][0] = np.inf
        unser = read_json(df.to_json())
        self.assertTrue(np.isnan(unser[2][0]))
        unser = read_json(df.to_json(), dtype=False)
        self.assertTrue(np.isnan(unser[2][0]))

        df[2][0] = np.NINF
        unser = read_json(df.to_json())
        self.assertTrue(np.isnan(unser[2][0]))
        unser = read_json(df.to_json(),dtype=False)
        self.assertTrue(np.isnan(unser[2][0]))

    def test_frame_to_json_except(self):
        df = DataFrame([1, 2, 3])
        self.assertRaises(ValueError, df.to_json, orient="garbage")

    def test_v12_compat(self):
        df = DataFrame(
            [[1.56808523,  0.65727391,  1.81021139, -0.17251653],
             [-0.2550111, -0.08072427, -0.03202878, -0.17581665],
             [1.51493992,  0.11805825,  1.629455, -1.31506612],
             [-0.02765498,  0.44679743,  0.33192641, -0.27885413],
             [0.05951614, -2.69652057,  1.28163262,  0.34703478]],
            columns=['A', 'B', 'C', 'D'],
            index=pd.date_range('2000-01-03', '2000-01-07'))
        df['date'] = pd.Timestamp('19920106 18:21:32.12')
        df.ix[3, 'date'] = pd.Timestamp('20130101')
        df['modified'] = df['date']
        df.ix[1, 'modified'] = pd.NaT

        v12_json = os.path.join(self.dirpath, 'tsframe_v012.json')
        df_unser = pd.read_json(v12_json)
        df_unser = pd.read_json(v12_json)
        assert_frame_equal(df, df_unser)

        df_iso = df.drop(['modified'], axis=1)
        v12_iso_json = os.path.join(self.dirpath, 'tsframe_iso_v012.json')
        df_unser_iso = pd.read_json(v12_iso_json)
        assert_frame_equal(df_iso, df_unser_iso)

    def test_series_non_unique_index(self):
        s = Series(['a', 'b'], index=[1, 1])

        self.assertRaises(ValueError, s.to_json, orient='index')

        assert_series_equal(s, read_json(s.to_json(orient='split'),
                            orient='split', typ='series'))
        unser = read_json(s.to_json(orient='records'),
                          orient='records', typ='series')
        np.testing.assert_equal(s.values, unser.values)

    def test_series_from_json_to_json(self):

        def _check_orient(series, orient, dtype=None, numpy=False):
            series = series.sort_index()
            unser = read_json(series.to_json(orient=orient),
                              typ='series', orient=orient, numpy=numpy,
                              dtype=dtype)
            unser = unser.sort_index()
            if orient == "records" or orient == "values":
                assert_almost_equal(series.values, unser.values)
            else:
                try:
                    assert_series_equal(series, unser)
                except:
                    raise
                if orient == "split":
                    self.assertEqual(series.name, unser.name)

        def _check_all_orients(series, dtype=None):
            _check_orient(series, "columns", dtype=dtype)
            _check_orient(series, "records", dtype=dtype)
            _check_orient(series, "split", dtype=dtype)
            _check_orient(series, "index", dtype=dtype)
            _check_orient(series, "values", dtype=dtype)

            _check_orient(series, "columns", dtype=dtype, numpy=True)
            _check_orient(series, "records", dtype=dtype, numpy=True)
            _check_orient(series, "split", dtype=dtype, numpy=True)
            _check_orient(series, "index", dtype=dtype, numpy=True)
            _check_orient(series, "values", dtype=dtype, numpy=True)

        # basic
        _check_all_orients(self.series)
        self.assertEqual(self.series.to_json(),
                         self.series.to_json(orient="index"))

        objSeries = Series([str(d) for d in self.objSeries],
                           index=self.objSeries.index,
                           name=self.objSeries.name)
        _check_all_orients(objSeries, dtype=False)
        _check_all_orients(self.empty_series)
        _check_all_orients(self.ts)

        # dtype
        s = Series(lrange(6), index=['a','b','c','d','e','f'])
        _check_all_orients(Series(s, dtype=np.float64), dtype=np.float64)
        _check_all_orients(Series(s, dtype=np.int), dtype=np.int)

    def test_series_to_json_except(self):
        s = Series([1, 2, 3])
        self.assertRaises(ValueError, s.to_json, orient="garbage")

    def test_series_from_json_precise_float(self):
        s = Series([4.56, 4.56, 4.56])
        result = read_json(s.to_json(), typ='series', precise_float=True)
        assert_series_equal(result, s)

    def test_frame_from_json_precise_float(self):
        df = DataFrame([[4.56, 4.56, 4.56], [4.56, 4.56, 4.56]])
        result = read_json(df.to_json(), precise_float=True)
        assert_frame_equal(result, df)

    def test_typ(self):

        s = Series(lrange(6), index=['a','b','c','d','e','f'], dtype='int64')
        result = read_json(s.to_json(),typ=None)
        assert_series_equal(result,s)

    def test_reconstruction_index(self):

        df = DataFrame([[1, 2, 3], [4, 5, 6]])
        result = read_json(df.to_json())

        # the index is serialized as strings....correct?
        assert_frame_equal(result, df)

    def test_path(self):
        with ensure_clean('test.json') as path:
            for df in [self.frame, self.frame2, self.intframe, self.tsframe,
                       self.mixed_frame]:
                df.to_json(path)
                read_json(path)

    def test_axis_dates(self):

        # frame
        json = self.tsframe.to_json()
        result = read_json(json)
        assert_frame_equal(result, self.tsframe)

        # series
        json = self.ts.to_json()
        result = read_json(json, typ='series')
        assert_series_equal(result, self.ts)

    def test_convert_dates(self):

        # frame
        df = self.tsframe.copy()
        df['date'] = Timestamp('20130101')

        json = df.to_json()
        result = read_json(json)
        assert_frame_equal(result, df)

        df['foo'] = 1.
        json = df.to_json(date_unit='ns')
        result = read_json(json, convert_dates=False)
        expected = df.copy()
        expected['date'] = expected['date'].values.view('i8')
        expected['foo'] = expected['foo'].astype('int64')
        assert_frame_equal(result, expected)

        # series
        ts = Series(Timestamp('20130101'), index=self.ts.index)
        json = ts.to_json()
        result = read_json(json, typ='series')
        assert_series_equal(result, ts)

    def test_date_format_frame(self):
        df = self.tsframe.copy()

        def test_w_date(date, date_unit=None):
            df['date'] = Timestamp(date)
            df.ix[1, 'date'] = pd.NaT
            df.ix[5, 'date'] = pd.NaT
            if date_unit:
                json = df.to_json(date_format='iso', date_unit=date_unit)
            else:
                json = df.to_json(date_format='iso')
            result = read_json(json)
            assert_frame_equal(result, df)

        test_w_date('20130101 20:43:42.123')
        test_w_date('20130101 20:43:42', date_unit='s')
        test_w_date('20130101 20:43:42.123', date_unit='ms')
        test_w_date('20130101 20:43:42.123456', date_unit='us')
        test_w_date('20130101 20:43:42.123456789', date_unit='ns')

        self.assertRaises(ValueError, df.to_json, date_format='iso',
                          date_unit='foo')

    def test_date_format_series(self):
        def test_w_date(date, date_unit=None):
            ts = Series(Timestamp(date), index=self.ts.index)
            ts.ix[1] = pd.NaT
            ts.ix[5] = pd.NaT
            if date_unit:
                json = ts.to_json(date_format='iso', date_unit=date_unit)
            else:
                json = ts.to_json(date_format='iso')
            result = read_json(json, typ='series')
            assert_series_equal(result, ts)

        test_w_date('20130101 20:43:42.123')
        test_w_date('20130101 20:43:42', date_unit='s')
        test_w_date('20130101 20:43:42.123', date_unit='ms')
        test_w_date('20130101 20:43:42.123456', date_unit='us')
        test_w_date('20130101 20:43:42.123456789', date_unit='ns')

        ts = Series(Timestamp('20130101 20:43:42.123'), index=self.ts.index)
        self.assertRaises(ValueError, ts.to_json, date_format='iso',
                          date_unit='foo')

    def test_date_unit(self):
        df = self.tsframe.copy()
        df['date'] = Timestamp('20130101 20:43:42')
        df.ix[1, 'date'] = Timestamp('19710101 20:43:42')
        df.ix[2, 'date'] = Timestamp('21460101 20:43:42')
        df.ix[4, 'date'] = pd.NaT

        for unit in ('s', 'ms', 'us', 'ns'):
            json = df.to_json(date_format='epoch', date_unit=unit)

            # force date unit
            result = read_json(json, date_unit=unit)
            assert_frame_equal(result, df)

            # detect date unit
            result = read_json(json, date_unit=None)
            assert_frame_equal(result, df)

    def test_weird_nested_json(self):
        # this used to core dump the parser
        s = r'''{
        "status": "success",
        "data": {
        "posts": [
            {
            "id": 1,
            "title": "A blog post",
            "body": "Some useful content"
            },
            {
            "id": 2,
            "title": "Another blog post",
            "body": "More content"
            }
           ]
          }
        }'''

        read_json(s)

    def test_doc_example(self):
        dfj2 = DataFrame(np.random.randn(5, 2), columns=list('AB'))
        dfj2['date'] = Timestamp('20130101')
        dfj2['ints'] = lrange(5)
        dfj2['bools'] = True
        dfj2.index = pd.date_range('20130101',periods=5)

        json = dfj2.to_json()
        result = read_json(json,dtype={'ints' : np.int64, 'bools' : np.bool_})
        assert_frame_equal(result,result)

    def test_misc_example(self):

        # parsing unordered input fails
        result = read_json('[{"a": 1, "b": 2}, {"b":2, "a" :1}]',numpy=True)
        expected = DataFrame([[1,2],[1,2]],columns=['a','b'])
        with tm.assertRaisesRegexp(AssertionError,
                                   '\[index\] left \[.+\], right \[.+\]'):
            assert_frame_equal(result, expected)

        result = read_json('[{"a": 1, "b": 2}, {"b":2, "a" :1}]')
        expected = DataFrame([[1,2],[1,2]],columns=['a','b'])
        assert_frame_equal(result,expected)

    @network
    def test_round_trip_exception_(self):
        # GH 3867
        csv = 'https://raw.github.com/hayd/lahman2012/master/csvs/Teams.csv'
        df = pd.read_csv(csv)
        s = df.to_json()
        result = pd.read_json(s)
        assert_frame_equal(result.reindex(index=df.index,columns=df.columns),df)

    @network
    def test_url(self):
        url = 'https://api.github.com/repos/pydata/pandas/issues?per_page=5'
        result = read_json(url, convert_dates=True)
        for c in ['created_at', 'closed_at', 'updated_at']:
            self.assertEqual(result[c].dtype, 'datetime64[ns]')

    def test_default_handler(self):
        from datetime import timedelta
        frame = DataFrame([timedelta(23), timedelta(seconds=5)])
        self.assertRaises(OverflowError, frame.to_json)
        expected = DataFrame([str(timedelta(23)), str(timedelta(seconds=5))])
        assert_frame_equal(
            expected, pd.read_json(frame.to_json(default_handler=str)))

        def my_handler_raises(obj):
            raise TypeError("raisin")
        self.assertRaises(TypeError, frame.to_json,
                          default_handler=my_handler_raises)
