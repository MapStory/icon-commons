from lxml import etree
import re


# @todo testme
def process_svg(svg, params):
    dom = etree.fromstring(str(svg))
    ns = {"svg": "http://www.w3.org/2000/svg"}
    fill = params.get('fill', None)
    stroke = params.get('stroke', None)
    # @todo process other elements
    for path in dom.xpath('//svg:path', namespaces=ns):
        style = path.get('style')
        # @todo make this better - use css library?
        style = re.sub('fill:[^;]+;', '', style)
        style = re.sub('stroke:[^;]+;', '', style)
        if fill:
            style += 'fill:%s;' % fill
        if stroke:
            style += 'stroke:%s;' % stroke
        path.set('style', style)
    return etree.tostring(dom)
