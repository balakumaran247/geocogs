from typing import List, Tuple
import ee
ee.Initialize()


def get_IITB_dr(year: int, span_step: str) -> List[List[Tuple[ee.Date, ee.Date, int]]]:
    """list holding the start date, end date and multiplication factor
    for each step as element for the span

    Args:
        year (int): year for filtering
        span_step (str): 'hyd_year', 'hyd_month', 'cal_year' or 'cal_month'
    """
    n = 1 if span_step in {'hyd_year', 'hyd_month'} else 0

    def leap(year, val, adj):
        if ((year % 400 == 0) or (year % 100 != 0) and (year % 4 == 0)):
            return val + adj
        else:
            return val

    IITB_monthly = {
        'jan': [(ee.Date.fromYMD(year+n, 1, 1), ee.Date.fromYMD(year+n, 1, 22), 8),
                (ee.Date.fromYMD(year+n, 1, 22), ee.Date.fromYMD(year+n, 1, 29), 7), ],  # jan
        'feb': [(ee.Date.fromYMD(year+n, 1, 22), ee.Date.fromYMD(year+n, 1, 29), 1),
                (ee.Date.fromYMD(year+n, 2, 1), ee.Date.fromYMD(year+n, 2, 22), 8),
                (ee.Date.fromYMD(year+n, 2, 23), ee.Date.fromYMD(year+n, 2, 28), leap(year+n, 3, 1))],  # feb
        'mar': [(ee.Date.fromYMD(year+n, 2, 23), ee.Date.fromYMD(year+n, 2, 28), leap(year+n, 5, -1)),
                (ee.Date.fromYMD(year+n, 3, 1), ee.Date.fromYMD(year+n, 3, 24), 8),
                (ee.Date.fromYMD(year+n, 3, 25), ee.Date.fromYMD(year+n, 4, 1), leap(year+n, 2, 1))],  # mar
        'apr': [(ee.Date.fromYMD(year+n, 3, 25), ee.Date.fromYMD(year+n, 4, 1), leap(year+n, 6, -1)),
                (ee.Date.fromYMD(year+n, 4, 1), ee.Date.fromYMD(year+n, 4, 26), 8),
                (ee.Date.fromYMD(year+n, 4, 26), ee.Date.fromYMD(year+n, 5, 3), leap(year+n, 0, 1))],  # apr
        'may': [(ee.Date.fromYMD(year+n, 4, 26), ee.Date.fromYMD(year+n, 5, 3), leap(year+n, 8, -1)),
                (ee.Date.fromYMD(year+n, 5, 3), ee.Date.fromYMD(year+n, 5, 20), 8),
                (ee.Date.fromYMD(year+n, 5, 21), ee.Date.fromYMD(year+n, 5, 29), leap(year+n, 7, 1))],  # may
        'jun': [(ee.Date.fromYMD(year, 5, 24), ee.Date.fromYMD(year, 5, 27), leap(year, 1, -1)),
                (ee.Date.fromYMD(year, 6, 1), ee.Date.fromYMD(year, 6, 20), 8),
                (ee.Date.fromYMD(year, 6, 21), ee.Date.fromYMD(year, 6, 29), leap(year, 5, 1))],  # june
        'jul': [(ee.Date.fromYMD(year, 6, 21), ee.Date.fromYMD(year, 6, 29), leap(year, 3, -1)),
                (ee.Date.fromYMD(year, 7, 1), ee.Date.fromYMD(year, 7, 23), 8),
                (ee.Date.fromYMD(year, 7, 24), ee.Date.fromYMD(year, 7, 29), leap(year, 4, 1))],  # july
        'aug': [(ee.Date.fromYMD(year, 7, 24), ee.Date.fromYMD(year, 7, 29), leap(year, 4, -1)),
                (ee.Date.fromYMD(year, 8, 1), ee.Date.fromYMD(year, 8, 25), 8),
                (ee.Date.fromYMD(year, 8, 26), ee.Date.fromYMD(year, 8, 30), leap(year, 3, 1))],  # aug
        'sep': [(ee.Date.fromYMD(year, 8, 26), ee.Date.fromYMD(year, 8, 30), leap(year, 5, -1)),
                (ee.Date.fromYMD(year, 9, 1), ee.Date.fromYMD(year, 9, 27), 8),
                (ee.Date.fromYMD(year, 9, 28), ee.Date.fromYMD(year, 10, 1), leap(year, 1, 1))],  # Sept
        'oct': [(ee.Date.fromYMD(year, 9, 28), ee.Date.fromYMD(year, 10, 1), leap(year, 7, -1)),
                (ee.Date.fromYMD(year, 10, 2), ee.Date.fromYMD(year, 10, 27), 8),
                (ee.Date.fromYMD(year, 10, 27), ee.Date.fromYMD(year, 11, 3), leap(year, 0, 1))],  # Oct
        'nov': [(ee.Date.fromYMD(year, 10, 29), ee.Date.fromYMD(year, 11, 3), leap(year, 8, -1)),
                (ee.Date.fromYMD(year, 11, 3), ee.Date.fromYMD(year, 11, 20), 8),
                (ee.Date.fromYMD(year, 11, 21), ee.Date.fromYMD(year, 11, 27), leap(year, 6, 1))],  # Nov
        'dec': [(ee.Date.fromYMD(year, 11, 21), ee.Date.fromYMD(year, 11, 27), leap(year, 2, -1)),
                (ee.Date.fromYMD(year, 12, 1), ee.Date.fromYMD(year, 12, 20), 8),
                (ee.Date.fromYMD(year, 12, 20), ee.Date.fromYMD(year, 12, 29), leap(year, 5, 1))],  # Dec
    }

    IITB_date_range = {
        'hyd_year': [
            [(ee.Date.fromYMD(year, 5, 24), ee.Date.fromYMD(year, 5, 27), leap(year, 1, -1)),
             (ee.Date.fromYMD(year, 6, 1), ee.Date.fromYMD(year, 12, 20), 8),
             (ee.Date.fromYMD(year, 12, 21), ee.Date.fromYMD(
                 year, 12, 30), leap(year, 5, 1)),
             (ee.Date.fromYMD(year+1, 1, 1), ee.Date.fromYMD(year+1, 5, 20), 8),
             (ee.Date.fromYMD(year+1, 5, 21), ee.Date.fromYMD(year+1, 5, 29), leap(year+1, 7, 1))]],
        'cal_year': [[
            (ee.Date.fromYMD(year, 1, 1), ee.Date.fromYMD(year, 12, 20), 8),
            (ee.Date.fromYMD(year, 12, 21), ee.Date.fromYMD(year, 12, 31), leap(year, 5, 1))]],
        'hyd_month': [value for value in IITB_monthly.values()],
        'cal_month': [value for value in IITB_monthly.values()],
    }

    return IITB_date_range[span_step]
