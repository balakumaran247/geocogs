"""csei-tools QGIS plugin - LULC Statistics tool
This script will help run the tool as batch process for
different shape files and no. of years.
"""
from qgis import processing
import os
from pathlib import Path

# folder path to multiple input shape files
shp_directory = r'C:\Users\atree\Desktop\shp'

# folder path to save the output CSV files
out_directory = r'C:\Users\atree\Desktop\CSV'

# input parameters
years = [2019] # years seperated by comma
parameters = {
    'COLNAME': 'id',  # unique field name
    'SPAN': 1,
}

# don't modify beyond this line
print('started...')
for year in years:
    out_path = Path.joinpath(Path(out_directory), str(year))
    out_path.mkdir(parents=True, exist_ok=True)
    for file in os.listdir(shp_directory):
        if os.path.splitext(file)[1] == '.shp':
            input_shp = os.path.join(shp_directory, file)
            # print(f'input file: {input_shp}')
            output_csv = os.path.join(
                out_path, f'{os.path.splitext(file)[0]}.csv')
            parameters.update(INPUT=input_shp, OUTPUT=output_csv, YEAR=year)
            processing.run("csei:lulc_stats", parameters)
            print(f'output file: {output_csv}')

print('completed!!!')