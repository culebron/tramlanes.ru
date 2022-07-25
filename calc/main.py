from fastkml import kml
from render import render
from shapely.geometry import LineString
import argh
import geopandas as gpd
import pandas as pd
import pyproj


CITIES_POPULATION = 'src/city-population.csv'
MUNICIPALITIES_BORDERS = 'src/muni.geojson'
NAMES_CORRECTIONS = 'src/alt-name-corrections.csv'
MOW_BORDERS = 'src/mow.geojson'
SPB_BORDERS = 'src/spb.geojson'
LANES_MAP_FILE = '/tmp/Обособление трамвая в РФ.kml'
RESULT_GEOJSON = 'build/tram-lanes.geojson'
RESULT_CSV = 'build/tram-lanes.csv'


WGS = 4326
SIB = pyproj.crs.ProjectedCRS(pyproj.crs.coordinate_operation.AlbersEqualAreaConversion(52, 64, 0, 105, 18500000, 0), name='Albers Siberia')


def match_cities(muni_df: gpd.GeoDataFrame, pop_df: pd.DataFrame):
	muni_df = muni_df[~muni_df['name'].str.contains('район').fillna(False)]
	def _m(n):
		if n is None:
			return

		l = n.lower().split()
		if not l or len(l) == 0:
			return

		for city_name in pop_df['name']:
			cnl = city_name.lower()
			if cnl in l:  # делим на массив, чтобы не искать во всей строке, иначе омск/томск путаются
				return city_name
			if cnl.endswith('ь'):
				words = set(l) - {'образование', 'округ', 'поселение', 'городской', 'муниципальное', 'муниципальный'}
				for w in words:
					if w.startswith(cnl[:-1]) and w in (cnl[:-1] + 'ский', cnl + 'ский'):
						print(n, 'matches', city_name)
						return city_name
			if ' ' in city_name and cnl in n.lower():  # если в имени из справочника населения есть пробел (набережные челны), тогда надо сравнить всю строку
				return city_name

	muni_df['short_name1'] = muni_df['name'].apply(_m)
	muni_df['short_name2'] = muni_df['alt_name'].fillna('').apply(_m)
	muni_df['short_name'] = muni_df['short_name1'].combine_first(muni_df['short_name2'])
	def find_pop(row):
		matching = pop_df[(pop_df['name'] == row['short_name1']) | (pop_df['name'] == row['short_name2'])]
		if not matching.empty:
			return matching['population'].values[0]

	muni_df['population'] = muni_df.apply(find_pop, axis=1)
	return muni_df[muni_df['short_name1'].notnull() | muni_df['short_name2'].notnull()]


@argh.dispatch_command
def render_page(outfile='build/index.html'):
	print('executing main')
	# параметр функции group_data - id карты гугла
	muni = gpd.read_file(MUNICIPALITIES_BORDERS)
	muni2 = muni.dissolve('name', {'alt_name': 'first'}).reset_index()

	# коррекция имён - добавляем alt_name где он необходим
	corrections = pd.read_csv(NAMES_CORRECTIONS)
	corrections_dict = dict(zip(corrections['name'].values, corrections['alt_name'].values))
	print(corrections_dict)
	muni2['alt_name'] = muni2.apply(lambda row: row['alt_name'] or corrections_dict.get(row['name'], None), axis=1)

	borders_file = pd.concat([muni2, gpd.read_file(MOW_BORDERS), gpd.read_file(SPB_BORDERS)])

	# if not os.path.exists(LANES_MAP_FILE):
	# 	map_id = '1DFLp5plaHPiIvVCgIWfb-cxRHJ9vBPg5'
	# 	print('downloading')
	# 	sh(f'wget "http://www.google.com/maps/d/kml?mid={map_id}&forcekml=1" -O {LANES_MAP_FILE}')

	k = kml.KML()
	# open & encoding - для декодирования файлов при открытии, потому что в системе по умолчанию может стоять кодировка ascii
	with open(LANES_MAP_FILE, encoding='utf-8') as f:
		# а плагин сам ещё раскодирует utf-8, поэтому закодировать обратно
		k.from_string(f.read().encode('utf-8'))

	data = []
	for f in list(k.features())[0].features():
		for f2 in f.features():
			data.append({'geometry': f2.geometry, 'layer': f.name})

	lanes = gpd.GeoDataFrame(data, crs=4326)

	LAYERS = {
		'Регионы. Обособлено знаками/разметкой/физически': 3,
		'Регионы. Нет обособления': 1,
		'Столицы. Обособлено знаками/разметкой/физически': 3,
		'Столицы. Нет обособления': 1,
		'План обособить в 2019': 2
	}

	print(lanes['layer'].unique())
	lanes['dedication'] = lanes['layer'].apply(lambda v: LAYERS.get(v, 1))
	lanes.drop('layer', axis=1, inplace=True)
	lanes['lanes_length'] = lanes['geometry'].to_crs(SIB).length
	lanes['dedicated_length'] = (lanes['dedication'] > 2) * lanes['lanes_length']

	populations = pd.read_csv(CITIES_POPULATION)
	matched_cities = match_cities(borders_file, populations)

	displayed_lanes = gpd.sjoin(lanes, matched_cities, how='inner', op='intersects')
	displayed_lanes = displayed_lanes[displayed_lanes['geometry'].geom_type == 'LineString'].copy()
	displayed_lanes = displayed_lanes[displayed_lanes['geometry'].apply(lambda g: len(g.coords) > 1)].copy()
	displayed_lanes['geometry'] = displayed_lanes['geometry'].apply(lambda g: LineString([xy[:2] for xy in list(g.coords)]))

	displayed_lanes.to_file(RESULT_GEOJSON)

	stat_table = displayed_lanes.dissolve('short_name', {'lanes_length': 'sum', 'dedicated_length': 'sum', 'population': 'first'}).reset_index()
	stat_table = pd.DataFrame(stat_table.join(stat_table.bounds).drop('geometry', axis=1).copy())
	stat_table['dedicated_share'] = stat_table['dedicated_length'] / stat_table['lanes_length']
	stat_table['rating'] = stat_table['dedicated_share'] * stat_table['dedicated_length']

	stat_table.sort_values('dedicated_share', ascending=False, inplace=True)

	stat_table.to_csv(RESULT_CSV, index=False)

	render('html/index.template.html', RESULT_GEOJSON, RESULT_CSV, outfile)
