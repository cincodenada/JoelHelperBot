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

yaml.Dumper.ignore_aliases = lambda *args : True

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
            info = {
                'year': '{}',
                'file': "File:ElectoralCollege{}.svg",
                'template': "Template:United_States_presidential_election,_{}_imagemap",
            }
            info = {k: v.format(y) for k, v in info.items()}
            info['filename'] = info['file'] + '.html'
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

                cacheinfo['sizes'] = self.get_size(html=info['html'])

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

    def get_size(self, base = 'full', html = None):
        #TODO: Take a year instead of explicit base
        sizes = {k:v for k,v in self.basedata[base].items() if k in ['width','height','thumbwidth','thumbheight']}
        if(html):
            soup = BeautifulSoup(html, 'html.parser')
            map_img = soup.find('img')
            if(map_img):
                sizes['width'] = int(map_img['data-file-width'])
                sizes['height'] = int(map_img['data-file-height'])
                sizes['thumbwidth'] = int(map_img['width'])
                sizes['thumbheight'] = int(map_img['height'])
        return sizes



mg = MapGetter(meta['bases'])
for curmap in mg.maps():
    base = meta['bases']['full']

    # Calculate scale the same way the ImageMap plugin does
    scale = (curmap['sizes']['thumbwidth']+curmap['sizes']['thumbheight'])/(curmap['sizes']['width']+curmap['sizes']['height'])

    outfile = open(os.path.join('gen', curmap['filename']),'w')
    outfile.write('<base href="http://en.wikipedia.org">\n')
    outfile.write("""<div class="center">
<div class="floatnone">
<div class="noresize" style="height: {}px; width: {}px;">
""".format(
        curmap['sizes']['thumbheight'], curmap['sizes']['thumbwidth']
    ))
    outfile.write('<map id="{0}" name="{0}">\n'.format(curmap['file']))
    for area_key in meta['area_sets']['full']:
        area = meta['areas'][area_key]
        icoords = (int(p) for p in area['points'].split(' '))
        coords = list(zip(icoords, icoords))
        adj_coords = []
        for pair in coords:
            for xy in range(2):
                adj_coords.append((pair[xy]*scale+base['offset'][xy])*base['scale'][xy])

        description = "United States presidential election in {}, {}".format(area['label'], curmap['year'])
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
