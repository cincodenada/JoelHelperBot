from Wikipedia import wikipedia
import yaml

meta = yaml.load(open('election_meta.yaml','r'))

wikipedia.set_lang('commons')
print("Getting list of maps...")
map_page = wikipedia.page('Template:US_presidential_election_maps_SVG')
# Not sure why I get all here, but whatevs
map_list = map_page.nslinks('File')
map_list = [l for l in map_list if l.startswith('File:')]

outfile = open('test.html','w')
curmap = map_list.pop()
base = meta['bases']['full']

print("Getting {}...".format(curmap))
curmap_page = wikipedia.page(curmap)
print("Getting thumbnail")
thumbs = curmap_page.query({
    'prop': 'imageinfo',
    'iiprop': 'url',
    'iiurlwidth': base['thumbwidth'],
})
thumb = next(thumbs)

scale = base['thumbwidth']/base['width']

outfile.write('<map id="testmap" name="testmap">\n')
for (state, area) in meta['areas']['full'].items():
    outfile.write('<area href="//en.wikipedia.org/wiki/United_States_presidential_election_in_{},_2016" shape="{}" coords="{}">\n'.format(
        state,
        area['shape'],
        ','.join([str(round(int(p)*scale)) for p in area['points'].split(' ')])
    ))
outfile.write('</map>\n')
outfile.write('<img src="{}" usemap="#testmap" width="349" height="203" />\n'.format(thumb['thumburl']))
outfile.close()
