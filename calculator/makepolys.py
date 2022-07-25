import argh
import os
import pyproj
import geopandas as gpd
import pandas as pd


SIB = pyproj.crs.ProjectedCRS(pyproj.crs.coordinate_operation.AlbersEqualAreaConversion(52, 64, 0, 105, 18500000, 0), name='Albers Siberia')

@argh.dispatch_command
def main(output_path):
	os.system('gs_exportosm russia-latest.osm.pbf --keep admin_level=6 --tags alt_name --tags short_name --tags wikipedia -l multipolygons /tmp/municip.gpkg')
	muni = gpd.read_file('/tmp/municip.gpkg')
	cities = muni[muni['name'].str.lower().contains('город')]
	cities2 = cities.to_crs(SIB)
	cities2['geometry'] = cities2['geomerty'].simplify(10)

	pop = pd.read_file('src/cities-raw.csv')
	def ff(n):
		i = cities2[cities2['name'].str.contains(n) | cities2['alt_name'].str.contains(n) | cities2['wikipedia'].str.contains(n)].index
		if len(i) > 0:
			return i[0]

	pop['pop_idx'] = pop['name'].apply(ff)
	pop.set_index('pop_idx', inplace=True)
	cities3 = cities2.join(pop)
	cities3.to_file(output_path)
