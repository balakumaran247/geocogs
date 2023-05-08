"""GeoCogs QGIS plugin - Coefficient of Variation tool
This script will help run the tool as batch process for
different shape files and no. of years.
"""
from qgis import processing
import os
from pathlib import Path
import time

# folder path to multiple input shape files
shp_directory = r'C:\Users\atree\Desktop\shp'

# folder path to save the output CSV files
out_directory = r'C:\Users\atree\Desktop\CSV'

# input parameters - list of (start_year, end_year)
years = [
    (2019, 2019),
    (2020, 2020),
    (2021, 2021),
]
parameters = {
    'START MONTH': 6,
    'END MONTH': 9,
    'PARAMETER': 0,
    'COLNAME': 'DISTRICT' # unique field name
}

# don't modify beyond this line
print('started...')
for year in years:
    start_year, end_year = year
    out_path = Path.joinpath(Path(out_directory), f"{str(start_year)}_{str(end_year)}")
    out_path.mkdir(parents=True, exist_ok=True)
    for file in os.listdir(shp_directory):
        if os.path.splitext(file)[1] == '.shp':
            input_shp = os.path.join(shp_directory, file)
            # print(f'input file: {input_shp}')
            output_csv = os.path.join(
                out_path, f'{os.path.splitext(file)[0]}.csv')
            parameters['INPUT'] = input_shp
            parameters['OUTPUT'] = output_csv
            parameters['START YEAR'] = start_year
            parameters['END YEAR'] = end_year
            processing.run("geocogs:coeff_var", parameters)
            print(f'{year} : {output_csv}')
    # time.sleep(300)

print('completed!!!')