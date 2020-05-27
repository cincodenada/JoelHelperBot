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
paths = tree.findall('.//*[@id="{}"]/*'.format(args.group_id))

states = {}
for p in paths:
  id = p.attrib['id']
  tag = p.tag.split('}')[1]
  out = {}
  out['label'] = ''
  if tag == 'rect':
    out['shape'] = 'rect'
    out['points'] = ' '.join([
      p.attrib['x'],
      p.attrib['y'],
      p.attrib['x'] + p.attrib['width'],
      p.attrib['y'] + p.attrib['height']
    ])
  else:
    out['shape'] = 'poly'
    toks = p.attrib['d'].split(' ')
    points = []

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

    out['points'] = ' '.join([str(round(float(n))) for n in points]) 
  states[id] = out

print(yaml.dump(states))
