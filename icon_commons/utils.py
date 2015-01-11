from lxml import etree
import re


_shape_paths = '|'.join(['//svg:%s' % e for e in ('path', 'polygon', 'circle', 'ellipse', 'rect', 'line', 'polyline')])


# @todo testme
def process_svg(svg, params):
    dom = etree.fromstring(str(svg))
    ns = {"svg": "http://www.w3.org/2000/svg"}
    fill = params.get('fill', None)
    stroke = params.get('stroke', None)
    replacers = []
    if fill:
        replacers.append(FillReplacer(fill))
    if stroke:
        replacers.append(StrokeReplacer(stroke))
    for el in dom.xpath(_shape_paths, namespaces=ns):
        process_element(el, replacers)
    return etree.tostring(dom)


def process_element(element, replacers):
    style = element.get('style')
    if style:
        styledict = dict([pv.split(':') for pv in style.split(';') if ':' in pv])
        if any([r.process(styledict) for r in replacers]):
            style = ';'.join(['%s:%s' % kv for kv in styledict.items()])
            element.set('style', style)
    # style may also be in element attributes
    for r in replacers:
        r.process(element.attrib)


class StyleReplacer(object):
    def __init__(self, replacement):
        self.replacement = replacement
        self.pattern = re.compile('%s:([^;]+);?' % self.property)

    def should_replace(self, style):
        return True

    def update(self, style):
        style[self.property] = self.replacement

    def process(self, style):
        updated = False
        if self.should_replace(style):
            self.update(style)
            updated = True
        return updated


class FillReplacer(StyleReplacer):
    property = 'fill'

    def should_replace(self, styles):
        fill = styles.get('fill', '').lower()
        return fill is None or (fill != 'none' and fill != '#ffffff')


class StrokeReplacer(StyleReplacer):
    property = 'stroke'

    def should_replace(self, styles):
        return True
