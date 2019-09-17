from xtopic import TopicElement

def isEmptyNode(node: TopicElement):
    if node.getTitle():
        return False
    if node.getFirstChildNodeByTagName('xhtml:img'):
        return False
    if node.getAttribute('xlink:href'):
        return False
    return True


# returns numbers 1 : 9 or letters starting with A starting at 10
def getId(xId):
    return chr(xId + 64)
