import sys
sys.path.append('../')

from Wikipedia import wikipedia
import pywikibot as pywiki
import yaml
from collections import OrderedDict
import os.path
from bs4 import BeautifulSoup
import re
from datetime import datetime
from io import StringIO
import argparse

# Lifted from http://stackoverflow.com/a/21912744/306323
def ordered_load(stream, Loader=yaml.Loader, object_pairs_hook=OrderedDict):
    class OrderedLoader(Loader):
        pass
    def construct_mapping(loader, node):
        loader.flatten_mapping(node)
        return object_pairs_hook(loader.construct_pairs(node))
    OrderedLoader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
        construct_mapping)
    return yaml.load(stream, OrderedLoader)

yaml.Dumper.ignore_aliases = lambda *args : True

meta = ordered_load(open('election_meta.yaml','r'))

class MapGetter:
    def __init__(self, basedata):
        self.basedata = basedata

    def get_years(self):
        print("Getting list of maps...")
        yield 1789
        for y in range(1792,2020,4):
            yield y

    def maps(self, start, end):
        cache = None
        try:
            cache = ordered_load(open('orig/metadata.yaml'))
        except IOError:
            pass
        if cache is None:
            cache = {}

        for y in self.get_years():
            if(y < start or y > end):
                continue

            info = {
                'year': '{}',
                'file': "File:ElectoralCollege{}.svg",
                'template': "Template:{}_United_States_presidential_election_imagemap",
            }
            info = {k: v.format(y) for k, v in info.items()}
            info['filename'] = info['file'] + '.html'
            info['base'] = self.get_base(y)

            origfile = os.path.join('orig', info['filename'])

            if(y in cache):
                print("Loading {} from cache...".format(y))
                cacheinfo = cache[y]
                info['html'] = open(origfile, 'r').read()
            else:
                print("Getting {}...".format(info['file']))

                cacheinfo = {}

                if(os.path.isfile(origfile)):
                    info['html'] = open(origfile,'r').read()
                else:
                    orig = open(origfile,'w')
                    wikipedia.set_lang('en')
                    try:
                        print("Downloading {}...".format(info['template']))
                        info['html'] = wikipedia.page(info['template']).html()
                        orig.write(info['html'])
                    except wikipedia.PageError:
                        info['html'] = None
                        orig.write('<!-- Page not found! -->')
                    orig.close()

                cacheinfo['sizes'] = self.get_size(info['base'], info['html'])

                wikipedia.set_lang('commons')
                curmap_page = wikipedia.page(info['file'])
                print("Getting thumbnail")
                thumbs = curmap_page.query({
                    'prop': 'imageinfo',
                    'iiprop': 'url',
                    'iiurlwidth': cacheinfo['sizes']['thumbwidth'],
                })
                thumb = next(thumbs)
                cacheinfo['thumb'] = str(thumb['thumburl'])
                cache[y] = cacheinfo
                yaml.dump(cache, open('orig/metadata.yaml','w'), default_flow_style=False)
            info.update(cacheinfo)
            yield info

    def get_base(self, year):
        for key, b in self.basedata.items():
            if(b['start'] <= year and ('end' not in b or b['end'] >= year)):
                return key
        return 'current'

    def get_size(self, base, html = None):
        sizes = self.basedata[base]['default_size']
        if(html):
            soup = BeautifulSoup(html, 'html.parser')
            map_img = soup.find('img')
            if(map_img):
                sizes['width'] = int(map_img['data-file-width'])
                sizes['height'] = int(map_img['data-file-height'])
                sizes['thumbwidth'] = int(map_img['width'])
                sizes['thumbheight'] = int(map_img['height'])
        return sizes


parser = argparse.ArgumentParser(description="Do some map stuff")
parser.add_argument('-m', '--edit-note', type=str, help="The edit message to send")
parser.add_argument('--cache-wiki', action="store_true", help="Cache wikitext. Do not use for actual edits, lest you get stale pages for comparison!")
parser.add_argument('--dry-run', action="store_true", help="Do a dry run - don't actually send any edits")
parser.add_argument('--start', type=int, default=1789, help="Year to start on")
parser.add_argument('--end', type=int, default=datetime.now().year, help="Year to end on")
args = parser.parse_args()

# Input an edit note interactively if we didn't get one
while not args.edit_note:
    args.edit_note = input('Edit note? ')

mg = MapGetter(meta['bases'])
enwiki = pywiki.Site('en')
for curmap in mg.maps(args.start, args.end):
    # Calculate scale the same way the ImageMap plugin does
    scale = (curmap['sizes']['thumbwidth']+curmap['sizes']['thumbheight'])/(curmap['sizes']['width']+curmap['sizes']['height'])
    base = meta['bases'][curmap['base']]

    outsvg = open(os.path.join('svg', curmap['filename'].replace('.html','')),'w')
    outsvg.write("""<svg xmlns="http://www.w3.org/2000/svg" width="{0}px" height="{1}px" viewBox="0 0 {0} {1}">
<style>
    /* <![CDATA[ */
    rect, polygon {{
      fill: none;
      stroke: black;
      stroke-width: 1px;
    }}
    /* ]]> */
</style>
""".format(curmap['sizes']['width'], curmap['sizes']['height']))

    outfile = open(os.path.join('gen', curmap['filename']),'w', encoding='utf-8')
    outfile.write('\ufeff') # TODO: This fixes test files, but does it break Wiki?
    outfile.write('<base href="http://en.wikipedia.org">\n')
    outfile.write("""<div class="center">
<div class="floatnone">
<div class="noresize" style="height: {}px; width: {}px;">
""".format(
        curmap['sizes']['thumbheight'], curmap['sizes']['thumbwidth']
    ))
    outfile.write('<map id="{0}" name="{0}">\n'.format(curmap['file']))

    outwiki = StringIO()
    outwiki.write('<imagemap>\n{}||{}px|center|\n\n'.format(
        curmap['file'].replace('File:','Image:'),
        curmap['sizes']['thumbwidth']
    ))
    origwiki_path = os.path.join('wiki', 'orig', curmap['template'])
    if(os.path.isfile(origwiki_path) and args.cache_wiki):
        origtext = open(origwiki_path, 'r').read()
    else:
        print("Downloading wikitext for {}...".format(curmap['template']))
        page = pywiki.Page(enwiki, curmap['template'])
        origtext = page.text
        origwiki = open(origwiki_path, 'w')
        origwiki.write(origtext)
        origwiki.close()

    to_remove = set()
    all_years = set()
    year_added = {}
    if 'additions' in base:
        all_years.update(base['additions'].keys())
        # Pre-remove any states that are added later
        for year, adds in base['additions'].items():
            for add in adds:
                if add not in year_added:
                    year_added[add] = year
            to_remove.update(adds)
    to_unremove = set()
    if 'removals' in base:
        all_years.update(base['removals'].keys())
        # ...but not states that are removed before being re-added
        for year, rems in base['removals'].items():
            to_unremove.update([rem for rem in rems if rem in year_added and year < year_added[rem]])

    to_remove.difference_update(to_unremove)

    for year in filter(lambda y: y <= int(curmap['year']), sorted(all_years)):
        if('removals' in base and year in base['removals']):
            print("Removing {} in {}".format(','.join(base['removals'][year]), year))
            to_remove.update(base['removals'][year])
        if('additions' in base and year in base['additions']):
            print("Adding {} in {}".format(','.join(base['additions'][year]), year))
            to_remove.difference_update(base['additions'][year])

    area_keys = [a for a in meta['area_sets'][curmap['base']] if a not in to_remove]

    for area_key in area_keys:
        area = meta['areas'][curmap['base']][area_key]

        # Get/adjust coords
        icoords = (int(p) for p in area['points'].split(' '))
        coords = list(zip(icoords, icoords))
        adj_coords = []
        for pair in coords:
            adj_pair = []
            for xy in range(2):
                adj_pair.append((pair[xy]*base['scale'][xy]+base['offset'][xy]))
            adj_coords.append(adj_pair)

        
        year = curmap['year']
        if year == "1789":
            year = "1788–89" # :(
        description = "{year} United States presidential election in {label}".format(label=area['label'], year=year)

        # Write HTML
        outfile.write(
            '<area href="/wiki/{}" shape="{}" coords="{}" alt="{}" title="{}" />\n'.format(
            description.replace(' ','_'),
            area['shape'],
            ','.join([str(round(c*scale)) for p in adj_coords for c in p]),
            description,
            description
        ))

        # Write debug SVG
        svg_id = re.sub(r"\W+","_",area_key)
        if(area['shape'] == 'rect'):
            outsvg.write('<rect id="{}" width="{}" height="{}" x="{}" y="{}"/>\n'.format(
                svg_id,
                adj_coords[1][0] - adj_coords[0][0],
                adj_coords[1][1] - adj_coords[0][1],
                adj_coords[0][0],
                adj_coords[0][1]
            ))
        elif(area['shape'] == 'poly'):
            points = ' '.join(','.join([str(round(p)) for p in pair]) for pair in adj_coords)
            outsvg.write('<polygon id="{}" points="{}"/>\n'.format(svg_id, points))

        # Write wikitext
        outwiki.write('{} {} [[{}]]\n'.format(
            area['shape'],
            ' '.join(' '.join([str(round(p)) for p in pair]) for pair in adj_coords),
            description
        ))

    outsvg.write('</svg>\n')

    outfile.write('</map>\n')
    outfile.write('<img alt="{}" src="{}" width="{}" height="{}" data-file-width="{}" data-file-height="{}" usemap="#{}"/>\n'.format(
        curmap['file'].replace('File:',''),
        curmap['thumb'].replace('https:',''),
        curmap['sizes']['thumbwidth'],
        curmap['sizes']['thumbheight'],
        curmap['sizes']['width'],
        curmap['sizes']['height'],
        curmap['file']
    ))
    outfile.write("""<div style="margin-left: {}px; margin-top: -20px; text-align: left;">
<a href="/wiki/{}" title="About this image">
<img alt="About this image" src="/w/extensions/ImageMap/desc-20.png?15600" style="border: none;" />
</a>
</div>
</div>
</div>
</div>
""".format(curmap['sizes']['thumbwidth']-20, curmap['file']))
    outfile.close()

    outwiki.write("""
</imagemap>
<noinclude>
[[Category:United States presidential election imagemaps]]
</noinclude>""")

    outwikifile = open(os.path.join('wiki', 'gen', curmap['template']),'w')
    outwikifile.write(outwiki.getvalue())
    outwikifile.close()

    if(origtext == outwiki.getvalue()):
        print("No changes found, continuing...")
    else:
        if(args.dry_run):
            print("Woulda submitted edit for {} with note {}".format(curmap['file'], args.edit_note))
        else:
            outpage = pywiki.Page(enwiki, curmap['template'])
            if(not outpage.exists() or (outpage.botMayEdit() and outpage.canBeEdited())):
                if(outpage.exists()):
                    print("Submitting edit for {}".format(curmap['template']))
                else:
                    print("Creating {}".format(curmap['template']))

                outpage.text = outwiki.getvalue()
                outpage.save(
                    summary = '{} (semi-automated)'.format(args.edit_note),
                    watch = 'watch',
                    minor = False,
                    botflag = True
                )
            else:
                print("Bot editing disallowed on {}, skipping...".format(curmap['template']))
