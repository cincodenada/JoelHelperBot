from Wikipedia import wikipedia
import yaml
from collections import OrderedDict

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

wikipedia.set_lang('commons')

class MapGetter:
    def __init__(self, fake):
        self.fake = fake

    def get_maps(self):
        print("Getting list of maps...")
        if(self.fake):
            yield "File:ElectoralCollege2016.svg"
            return

        map_page = wikipedia.page('Template:US_presidential_election_maps_SVG')
        # Not sure why I get all here, but whatevs
        for l in map_page.nslinks('File'):
            if l.startswith('File:'):
                yield l

    def maps(self):
        for m in self.get_maps():
            if(self.fake):
                yield {
                    'file': m,
                    'thumb': 'https://upload.wikimedia.org/wikipedia/commons/thumb/e/ec/ElectoralCollege2016.svg/349px-ElectoralCollege2016.svg.png',
                }
            else:
                print("Getting {}...".format(curmap))
                curmap_page = wikipedia.page(curmap)
                print("Getting thumbnail")
                thumbs = curmap_page.query({
                    'prop': 'imageinfo',
                    'iiprop': 'url',
                    'iiurlwidth': base['thumbwidth'],
                })
                thumb = next(thumbs)
                yield {
                    'file': m,
                    'thumb': thumb['thumburl']
                }


mg = MapGetter(True)
map_list = mg.get_maps()

outfile = open('test.html','w')
for curmap in mg.maps():
    base = meta['bases']['full']
    # Should be the same, but since we have them...
    scale = (
        base['thumbwidth']/base['width'],
        base['thumbheight']/base['height']
    )

    outfile.write('<map id="{0}" name="{0}">\n'.format(curmap['file']))
    for (state, area) in meta['areas']['full'].items():
        icoords = (int(p) for p in area['points'].split(' '))
        coords = list(zip(icoords, icoords))
        adj_coords = []
        for (x,y) in coords:
            adj_coords.append(x*scale[0]*1.03)
            adj_coords.append((y*scale[1]-7)*1.03)

        outfile.write('<area href="//en.wikipedia.org/wiki/United_States_presidential_election_in_{},_2016" shape="{}" coords="{}">\n'.format(
            state,
            area['shape'],
            ','.join([str(round(c)) for c in adj_coords])
        ))
    outfile.write('</map>\n')
    outfile.write('<img src="{}" usemap="#{}" width="349" height="203" />\n'.format(
        curmap['thumb'],
        curmap['file']
    ))
    outfile.close()
