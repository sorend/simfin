##########################################################################
#
# Various utility functions.
#
##########################################################################
# SimFin - Simple financial data for Python.
# www.simfin.com - www.github.com/simfin/simfin
# See README.md for instructions and LICENSE.txt for license details.
##########################################################################

import pandas as pd
import os
import time
from datetime import timedelta

from simfin.names import REPORT_DATE, TICKER

##########################################################################

def add_date_offset(df, date_index=REPORT_DATE, offset=pd.DateOffset(days=90)):
    """
    Add an offset to the date-index of a Pandas DataFrame.

    This is useful if you want to add a lag of e.g. 3 months
    (90 days) to the dates of financial reports such as Income
    Statements or Balance Sheets, because the REPORT_DATE is
    not when it was actually made available to the public.

    Typically there is a lag of 1, 2 or even 3 months between
    the REPORT_DATE and the actual date of publication. This
    function makes it easy to add such a lag to all reports.

    Although PUBLISH_DATE is supposed to be the actual date of
    publication, it can be misleading if there has been
    restatements to a financial report. Sometimes these can
    occur several years later, and because SimFin uses the
    newest data available, the PUBLISH_DATE is the date of the
    latest restatement rather than the first report, so the
    PUBLISH_DATE is not always useful.

    :param df:
        Pandas DataFrame assumed to have a MultiIndex
        containing dates in a column named `index_date`.

    :param date_index:
        Name of the date-column e.g. REPORT_DATE.

    :param offset:
        Offset to add to the dates. Use Pandas DateOffset.

    :return:
        Pandas DataFrame. Same as the input `df` except the
        dates in the index have been offset by the given amount.
    """

    # Perhaps there is a better way of doing this in Pandas?

    # Remove the column with dates from the index.
    df2 = df.reset_index(date_index)

    # Add the offset to the dates.
    df2[date_index] += offset

    # Reinsert the dates into the index.
    df2 = df2.set_index(date_index, append=True)

    return df2

##########################################################################

def apply(df, func, group_index=TICKER, **kwargs):
    """
    Apply a function to a Pandas DataFrame or Series with either a
    DatetimeIndex or MultiIndex. This is useful when you don't know
    whether a DataFrame contains data for a single or multiple stocks.

    You write your function to work for a DataFrame with a single stock,
    and this function lets you apply it to both DataFrames with a single
    or multiple stocks. The function automatically uses Pandas groupby to
    split-apply-merge on DataFrames with multiple stocks.

    :param df:
        Pandas DataFrame or Series assumed to have either a DatetimeIndex
        or a MultiIndex with 2 indices, one of which is a DatetimeIndex
        and the other is given by the arg `group_index`.

    :param func:
        Function to apply on a per-stock or per-group basis.
        The function is assumed to be of the form:

            def func(df_grp):
                # df_grp is a Pandas DataFrame with data for a single stock.
                # Perform some calculation on df_grp and create another
                # Pandas DataFrame or Series with the result and return it.
                # For example, we can calculate the cumulative sum:
                return df_grp.cumsum()

    :param group_index:
        If `df` has a MultiIndex then group data using this index-column.
        By default this is TICKER but it could also be e.g. SIMFIN_ID if
        you are using that as an index in your DataFrame.

    :param **kwargs:
        Optional keyword-arguments passed to `func`.

    :return:
        Pandas DataFrame or Series with the result of applying `func`.
    """

    assert isinstance(df, (pd.DataFrame, pd.Series))
    assert isinstance(df.index, (pd.DatetimeIndex, pd.MultiIndex))

    # If the DataFrame has a DatetimeIndex.
    if isinstance(df.index, pd.DatetimeIndex):
        df_result = func(df, **kwargs)

    # If the DataFrame has a MultiIndex.
    elif isinstance(df.index, pd.MultiIndex):
        # Helper-function for a DataFrame with a single group.
        def _apply_group(df_grp):
            # Remove group-index (e.g. TICKER) from the MultiIndex.
            df_grp = df_grp.reset_index(group_index, drop=True)

            # Perform the operation on this group.
            df_grp_result = func(df_grp, **kwargs)

            return df_grp_result

        # Split the DataFrame into sub-groups and perform
        # the operation on each sub-group and glue the
        # results back together into a single DataFrame.
        df_result = df.groupby(group_index).apply(_apply_group)

    return df_result

##########################################################################

def rename_columns(df, new_names, inplace=False):
    """
    Rename the columns in a Pandas DataFrame or Series. This function
    is useful because the syntax is slightly different for DataFrame and
    Series (this is one of many annoying inconsistencies in Pandas).

    :param df:
        Pandas DataFrame or Series.

    :param new_names:
        If `df` is a DataFrame then this is e.g. a dict mapping old
        names to new, such as:
            {'Old Name 1': 'New Name 1', 'Old Name 2': 'New Name 2'}

        If `df` is a Series then this is expected to be a single string.

    :param inplace:
        Boolean whether to update `df` inplace.

    :return:
        Pandas DataFrame or Series. Same as `df` except with the new names.

        There seems to be a bug in Pandas. If `df` is a DataFrame then
        it returns None if `inplace=True`, but if `df` is a Series then
        it returns the same Series if `inplace=True`.
        https://github.com/pandas-dev/pandas/issues/30211
    """

    if isinstance(df, pd.DataFrame):
        # Rename columns in a DataFrame.
        df = df.rename(columns=new_names, inplace=inplace)
    elif isinstance(df, pd.Series):
        # If new_names is not a string, then Pandas Series apparently tries
        # to rename the rows instead of the column, and it hangs the computer.
        assert isinstance(new_names, str)

        # Rename the single "column" of a Series.
        df = df.rename(new_names, inplace=inplace)

    return df

##########################################################################
# Functions for file-dates.

def file_age(path):
    """
    Return the age of the file with the given path, as the difference
    between the current time minus the file's last modification time.

    To get the file's age as the number of days call `file_age(path).days`

    Note that the file is assumed to exist, otherwise an exception is raised.
    Use `os.path.exists(path)` to check this before calling this function.

    :param path:
        String with full path of the file.

    :return:
        `datetime.timedelta` object.
    """

    # Last time the file was modified.
    file_timestamp = os.path.getmtime(path)

    # Difference between now and when the file was last modified.
    time_dif = time.time() - file_timestamp
    time_dif = timedelta(seconds=int(round(time_dif)))

    return time_dif


def is_file_newer(path, other_paths, no_exist=True):
    """
    Check whether the file located in `path` is newer than all the files
    located in `other_paths`.

    :param path:
        String with full path for the file.

    :param other_paths:
        String or list of strings with full paths for other files.

    :param no_exist:
        Boolean to use for files that do not exist.

    :return:
        Boolean.
    """

    # Convert string to list of strings, so we can use the same code below.
    if isinstance(other_paths, str):
        other_paths = [other_paths]

    # Timestamp for when the file was last modified.
    file_timestamp = os.path.getmtime(path)

    # Initialize the return-value.
    is_newer = True

    for other_path in other_paths:
        try:
            # Timestamp for when the other file was last modified.
            other_timestamp = os.path.getmtime(other_path)

            # Update the return-value.
            is_newer &= (file_timestamp > other_timestamp)
        except FileNotFoundError:
            # Other file did not exist, use the default boolean value.
            is_newer &= no_exist

        # Break out of the for-loop if we know the return-value will be False.
        if not is_newer:
            break

    return is_newer


def is_file_older(**kwargs):
    """
    Check whether the file located in `path` is older than all the files
    located in `other_paths`. This is a simple wrapper for `is_file_newer`.

    :param kwargs: Keyword args passed to `is_file_newer`.
    :return: Boolean.
    """
    return not is_file_newer(**kwargs)

##########################################################################

def is_str_or_list_str(s):
    """
    Return boolean whether `s` is a string or list of strings.
    """
    return isinstance(s, str) or \
          (isinstance(s, list) and all(isinstance(x, str) for x in s))

##########################################################################

def func_name(func):
    """
    Return the name of the function, or None if `func` is None.
    """
    return None if func is None else func.__name__

##########################################################################
