from html.element import Text, Element
from utils.fonts import get_font
from utils.config import Config
from utils.shape import Rect


class TextLayout:
    def __init__(self, node, word, parent, previous):
        self.node = node
        self.word = word
        self.children = []
        self.parent = parent
        self.previous = previous

        self.width = 0
        self.height = 0
        self.x = 0
        self.y = 0
        self.font = None

    def layout(self):
        weight = self.node.style["font-weight"]
        style = self.node.style["font-style"]
        if style == "normal":
            style = "roman"
        size = int(float(self.node.style["font-size"][:-2]) * .75)
        self.font = get_font(size, weight, style)

        self.width = self.font.measure(self.word)

        if self.previous:
            space = self.previous.font.measure(" ")
            self.x = self.previous.x + self.previous.width + space
        else:
            self.x = self.parent.x

        self.height = self.font.metrics("linespace")

    def paint(self):
        color = self.node.style["color"]
        return [DrawText(self.x, self.y, self.word, self.font, color)]


class LineLayout:
    def __init__(self, node, parent, previous):
        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []

        self.width = 0
        self.height = 0
        self.x = 0
        self.y = 0

    def layout(self):
        # Calculate width, x, y. Height will be calculated later after laying out the children
        self.width = self.parent.width
        self.x = self.parent.x

        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y

        for word in self.children:
            word.layout()

        if self.children:
            max_ascent = max([word.font.metrics("ascent") for word in self.children])
            baseline = self.y + 1.25 * max_ascent
            for word in self.children:
                word.y = baseline - word.font.metrics("ascent")
            max_descent = max([word.font.metrics("descent")
                               for word in self.children])

            self.height = 1.25 * (max_ascent + max_descent)

    def paint(self):
        return []


class DocumentLayout:
    def __init__(self, node):
        self.node = node
        self.parent = None
        self.children = []

        self.x = 0
        self.y = 0
        self.width = None
        self.height = None

    def layout(self):
        self.width = Config.width - 2 * Config.HSTEP
        self.x = Config.HSTEP
        self.y = Config.VSTEP

        child = BlockLayout(self.node, self, None)
        self.children.append(child)
        child.layout()
        self.height = child.height

    def paint(self):
        return []


class BlockLayout:
    def __init__(self, node, parent, previous, view_source=False):
        self.view_source = view_source
        self.display_list = []
        self.cursor_x = 0
        self.cursor_y = 0
        self.weight = "normal"
        self.style = "roman"
        self.size = 12
        self.line = []
        self.sup = False

        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []

        self.x = 0
        self.y = 0
        self.width = None
        self.height = None

    def new_line(self):
        self.cursor_x = 0
        last_line = self.children[-1] if self.children else None
        new_line = LineLayout(self.node, self, last_line)
        self.children.append(new_line)

    def layout_mode(self):
        """
        Return the layout mode of this node.

        If this node is Text, return `inline`
        Else if any of the children is in BLOCK_ELEMENTS than return `block`.
        Else if node has any children, return `inline`
        Else return `block`
        :return:
        """
        if isinstance(self.node, Text):
            return "inline"
        elif any([isinstance(child, Element) and child.tag in Config.BLOCK_ELEMENTS for child in self.node.children]):
            return "block"
        elif self.node.children:
            return "inline"
        else:
            return "block"

    def layout(self):
        self.x = self.parent.x
        self.width = self.parent.width

        if self.previous:
            self.y = self.previous.y + self.previous.height
        else:
            self.y = self.parent.y

        mode = self.layout_mode()
        if mode == "block":
            previous = None
            for child in self.node.children:
                next_ = BlockLayout(child, self, previous)
                self.children.append(next_)
                previous = next_
        else:
            self.new_line()
            self.recurse(self.node)
        for child in self.children:
            child.layout()

        self.height = sum([child.height for child in self.children])

    def word(self, node, word):
        weight = node.style["font-weight"]
        style = node.style["font-style"]
        if style == "normal":
            style = "roman"
        size = int(float(node.style["font-size"][:-2]) * .75)
        font_ = get_font(size if not self.sup else int(size / 2), weight, style)
        w = font_.measure(word)

        if self.cursor_x + w > self.width:
            self.new_line()

        # self.line.append((self.cursor_x, word, font_, color, self.sup))
        line = self.children[-1]
        previous_word = line.children[-1] if line.children else None
        text = TextLayout(node, word, line, previous_word)
        line.children.append(text)

        self.cursor_x += w + font_.measure(" ")

    def recurse(self, node):
        """
        Recurse through the child nodes in the HTML tree to layout words
        :param node:
        :return:
        """
        if isinstance(node, Text):
            for word in node.text.split():
                self.word(node, word)
        else:
            if node.tag == "br":
                self.flush()
            for child in node.children:
                self.recurse(child)

    def flush(self, center=False):
        if not self.line:
            return

        if center:
            center_offset = (Config.width - Config.HSTEP - self.cursor_x) / 2
        else:
            center_offset = 0

        # Find the tallest word
        metrics = [font_.metrics() for x, word, font_, color, sup in self.line]
        max_ascent = max([metric["ascent"] for metric in metrics])

        # Calculate baseline based on tallest word than place each word relative to that line
        baseline = self.cursor_y + 1.25 * max_ascent
        for rel_x, word, font_, color, sup in self.line:
            x = self.x + rel_x
            if sup:
                y = self.y + baseline - font_.metrics("ascent") * 2
            else:
                y = self.y + baseline - font_.metrics("ascent")
            self.display_list.append((x + center_offset, y, word, font_, color))

        # Move cursor_y far enough down below baseline to account for the deepest descender
        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = baseline + 1.25 * max_descent

        self.cursor_x = 0
        self.line = []

    def self_rect(self):
        return Rect(self.x, self.y, self.x + self.width, self.y + self.height)

    def paint(self):
        cmds = []
        # if isinstance(self.node, Element) and self.node.tag == "pre":
        #     x2, y2 = self.x + self.width, self.y + self.height
        #     rect = DrawRect(self.x, self.y, x2, y2, "gray")
        #     cmds.append(rect)
        # if self.layout_mode() == "inline":
        #     for x, y, word, font_, color in self.display_list:
        #         cmds.append(DrawText(x, y, word, font_, color))
        bgcolor = self.node.style.get("background-color",
                                      "transparent")
        if bgcolor != "transparent":
            rect = DrawRect(self.self_rect(), bgcolor)
            cmds.append(rect)
        return cmds


class DrawText:
    def __init__(self, x1, y1, text, font, color):
        self.top = y1
        self.left = x1
        self.text = text
        self.font = font
        self.color = color
        self.bottom = y1 + font.metrics("linespace")

    def execute(self, scroll, canvas):
        canvas.create_text(
            self.left, self.top - scroll,
            text=self.text,
            font=self.font,
            fill=self.color,
            anchor='nw'
        )


class DrawRect:
    def __init__(self, rect: Rect, color):
        self.left = rect.left
        self.right = rect.right
        self.top = rect.top
        self.bottom = rect.bottom
        self.color = color

    def execute(self, scroll, canvas):
        canvas.create_rectangle(
            self.left, self.top - scroll,
            self.right, self.bottom - scroll,
            width=0,
            fill=self.color)


class DrawOutline:
    def __init__(self, rect, color, thickness):
        self.rect = rect
        self.color = color
        self.thickness = thickness

    def execute(self, scroll, canvas):
        canvas.create_rectangle(
            self.rect.left, self.rect.top - scroll,
            self.rect.right, self.rect.bottom - scroll,
            width=self.thickness,
            outline=self.color)


class DrawLine:
    def __init__(self, x1, y1, x2, y2, color, thickness):
        self.rect = Rect(x1, y1, x2, y2)
        self.color = color
        self.thickness = thickness

    def execute(self, scroll, canvas):
        canvas.create_line(
            self.rect.left, self.rect.top - scroll,
            self.rect.right, self.rect.bottom - scroll,
            fill=self.color, width=self.thickness)
