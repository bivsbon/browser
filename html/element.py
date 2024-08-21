class Text:
    def __init__(self, text, parent):
        self.text = text
        self.children = []
        self.parent = parent
        self.style = {}

    def __repr__(self):
        return repr(self.text)


class Element:
    def __init__(self, tag: str, attributes: dict, parent):
        self.tag = tag
        self.attributes = attributes
        self.children = []
        self.parent = parent
        self.style = {}

    def __repr__(self):
        return "<" + self.tag + ">"
