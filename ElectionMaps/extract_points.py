from lxml import etree as ET
import re
import argparse
import yaml

parser = argparse.ArgumentParser(description="Extract points from an SVG to use for an HTML image map")
parser.add_argument('group_id', type=str, help="The SVG group to extract outlines from")
parser.add_argument('svg', type=str, help="SVG file to use as input")
args = parser.parse_args()

ET.register_namespace("wtf", "http://www.w3.org/2000/svg")
tree = ET.parse(args.svg)
root = tree.getroot()
paths = root.findall('.//*[@id="{}"]/*'.format(args.group_id))

abbrev_map = {
  "AL": "Alabama",
  "AK": "Alaska",
  "AZ": "Arizona",
  "AR": "Arkansas",
  "CA": "California",
  "CO": "Colorado",
  "CT": "Connecticut",
  "DE": "Delaware",
  "FL": "Florida",
  "GA": "Georgia",
  "HI": "Hawaii",
  "ID": "Idaho",
  "IL": "Illinois",
  "IN": "Indiana",
  "IA": "Iowa",
  "KS": "Kansas",
  "KY": "Kentucky",
  "LA": "Louisiana",
  "ME": "Maine",
  "MD": "Maryland",
  "MA": "Massachusetts",
  "MI": "Michigan",
  "MN": "Minnesota",
  "MS": "Mississippi",
  "MO": "Missouri",
  "MT": "Montana",
  "NE": "Nebraska",
  "NV": "Nevada",
  "NH": "New Hampshire",
  "NJ": "New Jersey",
  "NM": "New Mexico",
  "NY": "New York",
  "NC": "North Carolina",
  "ND": "North Dakota",
  "OH": "Ohio",
  "OK": "Oklahoma",
  "OR": "Oregon",
  "PA": "Pennsylvania",
  "RI": "Rhode Island",
  "SC": "South Carolina",
  "SD": "South Dakota",
  "TN": "Tennessee",
  "TX": "Texas",
  "UT": "Utah",
  "VT": "Vermont",
  "VA": "Virginia",
  "WA": "Washington",
  "WV": "West Virginia",
  "WI": "Wisconsin",
  "WY": "Wyoming",
}

# What the fuck viewbox
vb = [float(n) for n in root.attrib['viewBox'].split(' ')]

def transform(points):
  points = [float(n) for n in points]
  out = []
  while points:
    out.append(points.pop(0) - vb[0])
    out.append(points.pop(0) - vb[1])

  return [round(n) for n in out]

states = {}
for p in paths:
  id = p.attrib['id'].replace('O_','')
  tag = p.tag.split('}')[1]
  which = id.split('_')[0]
  if which in abbrev_map:
    which = abbrev_map[which]
  else:
    which = re.sub('([A-Z])',' \\1', which).strip()

  out = {}
  out['label'] = which
  points = []
  if tag == 'rect':
    out['shape'] = 'rect'
    points = [
      p.attrib['x'],
      p.attrib['y'],
      float(p.attrib['x']) + float(p.attrib['width']),
      float(p.attrib['y']) + float(p.attrib['height'])
    ]
  else:
    out['shape'] = 'poly'
    toks = p.attrib['d'].split(' ')

    mode = None
    x = None
    y = None
    while toks:
      tok = toks.pop(0)
      if re.match('^[A-Za-z]$', tok):
        if tok in ['M','L','H','V']:
          mode = tok
        elif tok == 'Z':
          break
        else:
          raise NotImplementedError("Unrecognized tag {}".format(tok))
      else:
        if mode == 'M' or mode == 'L':
          (x, y) = tok.split(',')
        elif mode == 'H':
          x = tok
        elif mode == 'V':
          y = tok
        else:
          raise NotImplementedError("Got numeric entry {} in bad mode {}".format(tok, mode))

        points.append(x);
        points.append(y);

  out['points'] = ' '.join([str(s) for s in transform(points)])
  states[id] = out

keys = list(states.keys());
keys.sort(key = lambda k: ' '.join((str(len(k.split('_'))), states[k]['label'])))
for key in keys:
  print(yaml.dump({key: states[key]}), end="")
