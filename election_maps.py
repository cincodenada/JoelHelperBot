from Wikipedia import wikipedia
import yaml
from collections import OrderedDict
import os.path

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
    def __init__(self, fake):
        self.fake = fake

    def get_years(self):
        print("Getting list of maps...")
        if(self.fake):
            yield 2012
            return

        yield 1789
        for y in range(1792,2020,4):
            yield y

    def maps(self):
        for y in self.get_years():
            info = {
                'year': '{}',
                'file': "File:ElectoralCollege{}.svg",
                'template': "Template:United_States_presidential_election,_{}_imagemap",
            }
            info = {k: v.format(y) for k, v in info.items()}
            if(self.fake):
                info['thumb'] = 'https://upload.wikimedia.org/wikipedia/commons/thumb/4/44/ElectoralCollege2012.svg/348px-ElectoralCollege2012.svg.png'
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
                info['thumb'] = thumb['thumburl']
            yield info

mg = MapGetter(True)
for curmap in mg.maps():
    base = meta['bases']['full']
    # Should be the same, but since we have them...
    scale = (
        base['thumbwidth']/base['width'],
        base['thumbheight']/base['height']
    )

    filename = curmap['file'] + '.html'
    origfile = os.path.join('orig', filename)
    if not os.path.isfile(origfile):
        orig = open(origfile,'w')
        wikipedia.set_lang('en')
        orig.write(wikipedia.page(curmap['template']).html())
        orig.close()

    outfile = open(os.path.join('gen', filename),'w')
    outfile.write('<base href="http://en.wikipedia.org">\n')
    outfile.write('<map id="{0}" name="{0}">\n'.format(curmap['file']))
    for (state, area) in meta['areas']['full'].items():
        icoords = (int(p) for p in area['points'].split(' '))
        coords = list(zip(icoords, icoords))
        adj_coords = []
        for pair in coords:
            for xy in range(2):
                adj_coords.append((pair[xy]*scale[xy]+base['offset'][xy])*base['scale'][xy])

        outfile.write('<area href="/wiki/United_States_presidential_election_in_{},_{}" shape="{}" coords="{}">\n'.format(
            state,
            curmap['year'],
            area['shape'],
            ','.join([str(round(c)) for c in adj_coords])
        ))
    outfile.write('</map>\n')
    outfile.write('<img src="{}" usemap="#{}" width="349" height="203" />\n'.format(
        curmap['thumb'],
        curmap['file']
    ))
    outfile.close()
