from ..geeassets import image_col, stat_dict
import pandas as pd
import numpy as np
import ee
ee.Initialize()
from qgis.core import QgsProcessingException, QgsMessageLog, Qgis
from ..utils import GeoCogsBase, logger, set_progressbar_perc, retry
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Tuple

class CoeffVariation(GeoCogsBase):
    """Coefficient of Variation
    Steps of Calculation:
    - calculate Area Weighted average (spatial) of pixels in an image
    - calculate the mean of AWA calculated over a time period of images
    - calculate the standard deviation of AWA calculated over a time period of images
    - calculate CV = std.dev / mean

    Args:
        GeoCogsBase (class): Base class of GeoCogs
    """
    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.featureCol = kwargs['featureCol']
        self.dataset = kwargs['dataset']
        self.start_year = kwargs['start_year']
        self.end_year = kwargs['end_year']
        self.start_month = kwargs['start_month']
        self.end_month = kwargs['end_month']
        self.col_name = kwargs['col_name']
        self.feedback = kwargs['feedback']
    
    def get_area_weighted_average(
        self,
        iColl: ee.ImageCollection,
        progress_start: int,
        progress_length: int) -> Dict[str,Dict[str,float]]:
        """Get Area weighted average of pixels in every image for the region

        Args:
            iColl (ee.ImageCollection): image collection
            progress_start (int): perc in progress bar before this method
            progress_length (int): perc difference allocated for this method

        Returns:
            Dict[str,Dict[str,float]]: dict of AWA for diff days of diff features
        """
        total = iColl.size().getInfo()
        logger(
            self.feedback,
            f'Total Images to Process for AWA: {total}',
            True)
        iColl_list = iColl.toList(total)
        spatial_reduce_func = self.spatial_reduce_setup('mean')
        awa_list = iColl_list.map(
            spatial_reduce_func
        )
        self.progress_iter = progress_length/total
        self.progress_start = progress_start+self.progress_iter
        @retry(5, 60, self.feedback)
        def get_data(count: int) -> Tuple[str, Dict[str, float]]:
            features = awa_list.get(count).getInfo()
            set_progressbar_perc(
                self.feedback,
                int(self.progress_start))
            self.progress_start+=self.progress_iter
            year = features['properties']['year']
            month = features['properties']['month']
            day = features['properties']['day']
            date = f"{year}{str(month).zfill(2)}{str(day).zfill(2)}"
            output = {}
            for feature in features['features']:
                name = feature['properties'][self.col_name]
                awa = feature['properties']['mean']
                output[name] = awa
            return date, output

        out_dict = {}
        with ThreadPoolExecutor() as ex:
            futures = [ex.submit(get_data, count) for count in range(total)]
        for future in as_completed(futures):
            date, out = future.result()
            out_dict[date] = out
        # for count in range(total):
        #     date, out = get_data(count)
        #     out_dict[date] = out
        return out_dict
    
    def get_awa_df(self, awa_dict: Dict[str,Dict[str,float]]) -> pd.DataFrame:
        """convert the Area weighted average dict to a pandas dataframe

        Args:
            awa_dict (Dict[str,Dict[str,float]]): AWA dictionary

        Returns:
            pd.DataFrame: AWA pandas dataframe
        """
        return pd.DataFrame(awa_dict)
    
    def save_awa_df(self, awa_df: pd.DataFrame, outpath: str):
        """save the AWA dataframe to CSV

        Args:
            awa_df (pd.DataFrame): AWA Pandas dataframe
            outpath (str): path to save the dataframe as CSV
        """
        awa_df.to_csv(outpath)
    
    def calc_std_dev(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate the standard deviation of AWA values over time period

        Args:
            df (pd.DataFrame): AWA dataframe

        Returns:
            pd.DataFrame: standard deviation dataframe
        """
        return df.std(axis=1).to_frame(name='std_dev')
    
    def calc_mean(self, df: pd.DataFrame) -> pd.DataFrame:
        """calculate teh mean of AWA values over time period

        Args:
            df (pd.DataFrame): AWA dataframe

        Returns:
            pd.DataFrame: Mean dataframe
        """
        return df.mean(axis=1).to_frame(name='mean')
    
    def join_dfs(self, std_df: pd.DataFrame, mean_df: pd.DataFrame) -> pd.DataFrame:
        """join the standard deviation and mean dataframe as single dataframe

        Args:
            std_df (pd.DataFrame): AWA standard deviation dataframe
            mean_df (pd.DataFrame): AWA mean dataframe

        Returns:
            pd.DataFrame: joined dataframe
        """
        return pd.concat([std_df, mean_df], axis=1)
    
    def calc_cv(self, df: pd.DataFrame) -> pd.DataFrame:
        """add a column for calcuated CV value by dividing standard deviation
        with mean

        Args:
            df (pd.DataFrame): joined dataframe

        Returns:
            pd.DataFrame: dataframe with std.dev, mean and CV columns
        """
        df['CV'] = df['std_dev'] / df['mean']
        return df
    
    def save_cv_df(self, df: pd.DataFrame, out_path: str):
        """save the CV dataframe as CSV

        Args:
            df (pd.DataFrame): CV dataframe
            out_path (str): path to save the CV dataframe as CSV
        """
        df.to_csv(out_path)