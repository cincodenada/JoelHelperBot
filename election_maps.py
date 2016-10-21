from Wikipedia import wikipedia

wikipedia.set_lang('commons')
map_page = wikipedia.page('Template:US_presidential_election_maps_SVG')
# Not sure why I get all here, but whatevs
map_list = map_page.nslinks('File')
map_list = [l for l in map_list if l.startswith('File:')]
