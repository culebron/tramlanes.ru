import argh
import geopandas as gpd
import pandas as pd
from jinja2 import Environment, FileSystemLoader, select_autoescape
env = Environment(
	loader=FileSystemLoader('./html'),
	autoescape=select_autoescape(['html', 'xml'])
)

def render(template, lanes_df, stats_df, html_target):
	threshold = 400_000
	big_cities = stats_df[stats_df['population'] > threshold].copy()
	small_cities = stats_df[stats_df['population'] <= threshold].copy()

	print('big:', len(big_cities))
	print('small:', len(small_cities))
	print('columns of cities:', list(big_cities))

	rendered = template.render(cities_json=lanes_df.to_json(), big_cities=big_cities.to_dict(orient='records'), small_cities=small_cities.to_dict(orient='records'))
	
	with open(html_target, 'w', encoding='utf-8') as f:
		f.write(rendered)

def render_cli(template_path, displayed_lanes, stat_table, output_path):
	template = env.get_template(template_path.replace('html/', ''))
	lanes = gpd.read_file(displayed_lanes)
	stats = pd.read_csv(stat_table)
	return render(template, lanes, stats, output_path)

if __name__ == '__main__':
	argh.dispatch_command(render_cli)
