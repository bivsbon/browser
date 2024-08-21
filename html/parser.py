from html.element import Text, Element


class HTMLParser:
    SELF_CLOSING_TAGS = [
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    ]
    HEAD_TAGS = [
        "base", "basefont", "bgsound", "noscript",
        "link", "meta", "title", "style", "script",
    ]
    NO_NEST_TAG = [
        "p", "li"
    ]
    VALID_FOLLOWER_SCRIPT_TAG = [" ", "\t", "\v", "\r", ">"]

    def __init__(self, body):
        self.body = body
        self.unfinished = []

    def find_next_script_close_tag(self, i: int, b: str) -> (int, int):
        """
        Find position of the next </script> tag
        :param i: start position
        :param b: the content of html page
        :return: start and end position of next </script> tag
        """
        cursor = i
        while True:
            potential = b.find("</script", cursor)
            if potential == -1:
                return -1, -1
            elif b[potential + 8] in self.VALID_FOLLOWER_SCRIPT_TAG:
                return potential, b.find(">", potential) + 1
            cursor = potential+1

    def parse(self):
        text = ""
        in_tag = False
        b = self.body
        i = 0
        while i < len(b):
            if b[i] == "<":
                in_tag = True
                if text:
                    self.add_text(text)
                text = ""
            elif b[i] == ">":
                if text == "script":
                    s, e = self.find_next_script_close_tag(i, b)
                    self.add_tag("script")
                    self.add_text(b[i+1:s])
                    self.add_tag(b[s+1:e-1])
                    i = e
                    text = ""
                else:
                    self.add_tag(text)
                    text = ""
                in_tag = False
            else:
                text += b[i]
            i += 1
        if not in_tag and text:
            self.add_text(text)
        return self.finish()

    def add_text(self, text: str):
        if text.isspace():
            return
        self.implicit_tags(None)
        parent = self.unfinished[-1]
        node = Text(text, parent)
        parent.children.append(node)

    def add_tag(self, tag: str):
        tag, attributes = self.get_attributes(tag)
        if tag.startswith("!"):
            return
        self.implicit_tags(tag)
        if tag.startswith("/"):
            if len(self.unfinished) == 1:
                return
            if tag[1:] in self.NO_NEST_TAG:
                nodes = [self.unfinished.pop()]
                while self.unfinished[-1].tag == tag[1:]:
                    nodes.append(self.unfinished.pop())
                parent = self.unfinished[-1]
                parent.children += nodes
            else:
                # Check if the closing tag match
                mismatch_tags = []
                while self.unfinished[-1].tag != tag[1:]:
                    mismatch_tags.append(self.unfinished[-1].tag)
                    self.add_tag("/" + self.unfinished[-1].tag)

                node = self.unfinished.pop()
                parent = self.unfinished[-1]
                parent.children.append(node)

                # Reopen the mismatch tags
                for tag in reversed(mismatch_tags):
                    self.add_tag(tag)
        elif tag in self.SELF_CLOSING_TAGS:
            parent = self.unfinished[-1]
            node = Element(tag, attributes, parent)
            parent.children.append(node)
        else:
            parent = self.unfinished[-1] if self.unfinished else None
            node = Element(tag, attributes, parent)
            self.unfinished.append(node)

    def finish(self):
        if not self.unfinished:
            self.implicit_tags(None)
        while len(self.unfinished) > 1:
            node = self.unfinished.pop()
            parent = self.unfinished[-1]
            parent.children.append(node)
        return self.unfinished.pop()

    def get_attributes(self, text: str):
        parts = text.split()
        tag = parts[0].casefold()
        attributes = {}
        for attrpair in parts[1:]:
            if "=" in attrpair:
                key, value = attrpair.split("=", 1)
                if len(value) > 2 and value[0] in ["'", "\""]:
                    value = value[1:-1]
                attributes[key.casefold()] = value
            else:
                attributes[attrpair.casefold()] = ""
        return tag, attributes

    def implicit_tags(self, tag):
        while True:
            open_tags = [node.tag for node in self.unfinished]
            if open_tags == [] and tag != "html":
                self.add_tag("html")
            elif open_tags == ["html"] and tag not in ["head", "body", "/html"]:
                if tag in self.HEAD_TAGS:
                    self.add_tag("head")
                else:
                    self.add_tag("body")
            elif open_tags == ["html", "head"] and tag not in ["/head"] + self.HEAD_TAGS:
                self.add_tag("/head")
            else:
                break


