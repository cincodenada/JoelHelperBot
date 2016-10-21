from Wikipedia import wikipedia
import yaml

meta = yaml.load(open('election_meta.yaml','r'))

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
    scale = base['thumbwidth']/base['width']

    outfile.write('<map id="{0}" name="{0}">\n'.format(curmap['file']))
    for (state, area) in meta['areas']['full'].items():
       outfile.write('<area href="//en.wikipedia.org/wiki/United_States_presidential_election_in_{},_2016" shape="{}" coords="{}">\n'.format(
           state,
           area['shape'],
           ','.join([str(round(int(p)*scale)) for p in area['points'].split(' ')])
    outfile.write('</map>\n')
    outfile.write('<img src="{}" usemap="#{}" width="349" height="203" />\n'.format(
        curmap['thumb'],
        curmap['file']
    ))
    outfile.close()
