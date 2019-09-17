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
def findQuestionDicts(answer: TopicElement, ref):
    followRels = answer.getSubTopics()
    questionDicts = []
    for followRel in followRels:
        if isEmptyNode(followRel):
            for nextA in followRel.getSubTopics():
                nextQPairs = findQuestionDicts(
                    answer=nextA, ref=ref + '<li>' + nextA.getTitle())
                questionDicts.extend(nextQPairs)
        else:
            questionDicts.append(dict(question=followRel, ref=ref))
    return questionDicts


# receives a question node and returns a list of dictionaries containing the
# subtopics and whether the subtopics contain an answer or not
def findAnswerDicts(question: TopicElement):
    answerDicts = list()
    for subTopic in question.getSubTopics():
        isAnswer = True
        if isEmptyNode(subTopic):
            isAnswer = False
        answerDicts.append(dict(subTopic=subTopic, isAnswer=isAnswer, aId=str(0)))
    return answerDicts
