from xtopic import TopicElement


# checks whether a node contains any text, images or link
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


# receives an answer node and returns all questions following this answer
# including questions following multiple topics
def findQuestions(answer: TopicElement, ref):
    followRels = answer.getSubTopics()
    questionDicts = []
    for followRel in followRels:
        if isEmptyNode(followRel):
            for nextA in followRel.getSubTopics():
                nextQPairs = findQuestions(
                    answer=nextA, ref=ref + '<li>' + nextA.getTitle())
                questionDicts.extend(nextQPairs)
        else:
            questionDicts.append(dict(question=followRel, ref=ref))
    return questionDicts


# receives a question node and returns all Answers that are not empty nodes
def findAnswers(question: TopicElement):
    answers = list()
    for answer in question.getSubTopics():
        if not(isEmptyNode(answer)):
            answers.append(answer)
    return answers