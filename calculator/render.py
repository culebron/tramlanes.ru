import argh
import geopandas as gpd
import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape
env = Environment(
	loader=FileSystemLoader('./html'),
	autoescape=select_autoescape(['html', 'xml'])
)

@argh.dispatch_command
def do(html_template, lanes_path, stats_path, html_target):
	lanes_df = gpd.read_file(lanes_path)
	stats_df = pd.read_csv(stats_path)

	tpl = env.get_template(html_template.replace('html/', ''))

	threshold = 400_000
	big_cities = stats_df[stats_df['population'] > threshold].copy()
	small_cities = stats_df[stats_df['population'] <= threshold].copy()

	print('big:', len(big_cities))
	print('small:', len(small_cities))
	print('columns of cities:', list(big_cities))

	rendered = tpl.render(cities_json=lanes_df.to_json(), big_cities=big_cities.to_dict(orient='records'), small_cities=small_cities.to_dict(orient='records'))
	with open(html_target, 'w', encoding='utf-8') as f:
		f.write(rendered)
