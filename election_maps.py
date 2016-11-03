from Wikipedia import wikipedia
import yaml
from collections import OrderedDict
import os.path
from bs4 import BeautifulSoup

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

meta = ordered_load(open('election_meta.yaml','r'))

class MapGetter:
    def __init__(self, basedata, years = None):
        self.basedata = basedata
        self.years = years

    def get_years(self):
        print("Getting list of maps...")
        if(self.years):
            for y in years:
                yield y
            return

        yield 1789
        for y in range(1792,2020,4):
            yield y

    def maps(self):
        cache = None
        try:
            cache = yaml.load(open('orig/metadata.yaml'))
        except IOError:
            pass
        if cache is None:
            cache = {}

        for y in self.get_years():
            # TODO: Filter by year
            base = self.basedata['full']
            info = {
                'year': '{}',
                'file': "File:ElectoralCollege{}.svg",
                'template': "Template:United_States_presidential_election,_{}_imagemap",
            }
            info = {k: v.format(y) for k, v in info.items()}
            if(y in cache):
                print("Loading {} from cache...".format(y))
                cacheinfo = cache[y]
            else:
                print("Getting {}...".format(info['file']))

                wikipedia.set_lang('commons')
                curmap_page = wikipedia.page(info['file'])
                print("Getting thumbnail")
                thumbs = curmap_page.query({
                    'prop': 'imageinfo',
                    'iiprop': 'url',
                    'iiurlwidth': base['thumbwidth'],
                })
                thumb = next(thumbs)
                cacheinfo = {
                    'thumb': str(thumb['thumburl']),
                }
                cache[y] = cacheinfo
                yaml.dump(cache, open('orig/metadata.yaml','w'), default_flow_style=False)
            info.update(cacheinfo)
            yield info

mg = MapGetter(meta['bases'])
for curmap in mg.maps():
    base = meta['bases']['full']

    filename = curmap['file'] + '.html'
    origfile = os.path.join('orig', filename)
    if os.path.isfile(origfile):
        html = open(origfile, 'r').read()
    else:
        orig = open(origfile,'w')
        wikipedia.set_lang('en')
        try:
            print("Downloading {}...".format(curmap['template']))
            html = wikipedia.page(curmap['template']).html()
            orig.write(html)
        except wikipedia.PageError:
            html = None
            orig.write('<!-- Page not found! -->')
        orig.close()

    if(html):
        soup = BeautifulSoup(html, 'html.parser')
        map_img = soup.find('img')
        if(map_img):
            base['width'] = int(map_img['data-file-width'])
            base['height'] = int(map_img['data-file-height'])
            base['thumbwidth'] = int(map_img['width'])
            base['thumbheight'] = int(map_img['height'])

    # Calculate scale the same way the ImageMap plugin does
    scale = (base['thumbwidth']+base['thumbheight'])/(base['width']+base['height'])

    outfile = open(os.path.join('gen', filename),'w')
    outfile.write('<base href="http://en.wikipedia.org">\n')
    outfile.write("""<div class="center">
<div class="floatnone">
<div class="noresize" style="height: {}px; width: {}px;">
""".format(
        base['thumbheight'], base['thumbwidth']
    ))
    outfile.write('<map id="{0}" name="{0}">\n'.format(curmap['file']))
    for area in meta['areas']['full']:
        icoords = (int(p) for p in area['points'].split(' '))
        coords = list(zip(icoords, icoords))
        adj_coords = []
        for pair in coords:
            for xy in range(2):
                adj_coords.append((pair[xy]*scale+base['offset'][xy])*base['scale'][xy])

        description = "United States presidential election in {}, {}".format(area['state'], curmap['year'])
        outfile.write(
            '<area href="/wiki/{}" shape="{}" coords="{}" alt="{}" title="{}" />\n'.format(
            description.replace(' ','_'),
            area['shape'],
            ','.join([str(round(c)) for c in adj_coords]),
            description,
            description
        ))
    outfile.write('</map>\n')
    outfile.write('<img alt="{}" src="{}" width="{}" height="{}" data-file-width="{}" data-file-height="{}" usemap="#{}"/>\n'.format(
        curmap['file'].replace('File:',''),
        curmap['thumb'].replace('https:',''),
        base['thumbwidth'],
        base['thumbheight'],
        base['width'],
        base['height'],
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
""".format(base['thumbwidth']-20, curmap['file']))
    outfile.close()
