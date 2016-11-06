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
    def __init__(self, basedata, default_size):
        self.basedata = basedata
        self.default_size = default_size

    def get_years(self, years):
        print("Getting list of maps...")
        if(years):
            for y in years:
                yield y
            return

        yield 1789
        for y in range(1792,2020,4):
            yield y

    def maps(self, years):
        cache = None
        try:
            cache = yaml.load(open('orig/metadata.yaml'))
        except IOError:
            pass
        if cache is None:
            cache = {}

        for y in self.get_years(years):
            info = {
                'year': '{}',
                'file': "File:ElectoralCollege{}.svg",
                'template': "Template:United_States_presidential_election,_{}_imagemap",
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

                cacheinfo['sizes'] = self.get_size(info['html'])

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

    def get_size(self, html = None):
        sizes = self.default_size
        if(html):
            soup = BeautifulSoup(html, 'html.parser')
            map_img = soup.find('img')
            if(map_img):
                sizes['width'] = int(map_img['data-file-width'])
                sizes['height'] = int(map_img['data-file-height'])
                sizes['thumbwidth'] = int(map_img['width'])
                sizes['thumbheight'] = int(map_img['height'])
        return sizes


# Get an edit note
editnote = None
while not editnote:
    editnote = input('Edit note? ')

mg = MapGetter(meta['bases'], meta['defaults'])
enwiki = pywiki.getSite('en')
for curmap in mg.maps(range(1848,2020,4)):
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

    outfile = open(os.path.join('gen', curmap['filename']),'w')
    outfile.write('<base href="http://en.wikipedia.org">\n')
    outfile.write("""<div class="center">
<div class="floatnone">
<div class="noresize" style="height: {}px; width: {}px;">
""".format(
        curmap['sizes']['thumbheight'], curmap['sizes']['thumbwidth']
    ))
    outfile.write('<map id="{0}" name="{0}">\n'.format(curmap['file']))

    outwiki = StringIO()
    outwiki.write('<!-- Generated by JoelHelperBot, {}-->\n<imagemap>\n{}||{}px|center|\n\n'.format(
        datetime.now().strftime('%H:%M, %d %b %Y'),
        curmap['file'].replace('File:','Image:'),
        curmap['sizes']['thumbwidth']
    ))
    origwiki_path = os.path.join('wiki', 'orig', curmap['template'])
    if(os.path.isfile(origwiki_path)):
        origtext = open(origwiki_path, 'r').read()
    else:
        print("Downloading wikitext for {}...".format(curmap['template']))
        page = pywiki.Page(enwiki, curmap['template'])
        origtext = page.text
        origwiki = open(origwiki_path, 'w')
        origwiki.write(origtext)
        origwiki.close()

    area_keys = list(meta['area_sets'][curmap['base']])
    if('additions' in base):
        for firstyear, keys in base['additions'].items():
            if(int(curmap['year']) < firstyear):
                for k in keys:
                    area_keys.remove(k)

    for area_key in area_keys:
        area = meta['areas'][area_key]

        # Get/adjust coords
        icoords = (int(p) for p in area['points'].split(' '))
        coords = list(zip(icoords, icoords))
        adj_coords = []
        for pair in coords:
            adj_pair = []
            for xy in range(2):
                adj_pair.append((pair[xy]*base['scale'][xy]+base['offset'][xy]))
            adj_coords.append(adj_pair)

        description = "United States presidential election in {}, {}".format(area['label'], curmap['year'])

        # Write HTML
        outfile.write(
            '<area href="/wiki/{}" shape="{}" coords="{}" alt="{}" title="{}" />\n'.format(
            description.replace(' ','_'),
            area['shape'],
            ','.join([str(round(c*scale)) for p in adj_coords for c in p]),
            description,
            description
        ))

        # Write SVG
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

    skipfirst = lambda s: ''.join(s.splitlines(True)[1:])
    if(skipfirst(origtext) == skipfirst(outwiki.getvalue())):
        print("No changes found, continuing...")
    else:
        outpage = pywiki.Page(enwiki, curmap['template'])
        if(outpage.botMayEdit() and outpage.canBeEdited()):
            print("Submitting edit for {}".format(curmap['template']))
            outpage.text = outwiki.getvalue()
            outpage.save(
                summary = '{} (semi-automated by JoelHelperBot)'.format(editnote),
                watch = 'watch',
                minor = False,
                botflag = True
            )
        else:
            print("Bot editing disallowed on {}, skipping...".format(curmap['template']))
