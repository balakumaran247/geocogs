from ..geeassets import image_col, stat_dict
import pandas as pd
import numpy as np
import ee
ee.Initialize()
from qgis.core import QgsProcessingException
from ..utils import GeoCogsBase

class CoeffVariation(GeoCogsBase):
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.featureCol = kwargs['featureCol']
        self.dataset = kwargs['dataset']
        self.start_year = kwargs['start_year']
        self.end_year = kwargs['end_year']
        self.start_month = kwargs['start_month']
        self.end_month = kwargs['end_month']
        self.col_name = kwargs['col_name']
    
    