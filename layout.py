from html.element import Text, Element
from utils.fonts import get_font
from utils.config import Config


class DocumentLayout:
    def __init__(self, node):
        self.node = node
        self.parent = None
        self.children = []

        self.x = None
        self.y = None
        self.width = None
        self.height = None
        self.max_scroll = None
        self.scroll_bar_x0 = None
        self.scroll_bar_x1 = None
        self.scroll_bar_height = None

    def layout(self):
        self.width = Config.width - 2 * Config.HSTEP
        self.x = Config.HSTEP
        self.y = Config.VSTEP

        child = BlockLayout(self.node, self, None)
        self.children.append(child)
        child.layout()
        self.height = child.height
        self.max_scroll = 0 if self.height - Config.height + 2*Config.VSTEP < 0 else self.height - Config.height + 2*Config.VSTEP
        self.scroll_bar_x0 = Config.width - Config.HSTEP + 2
        self.scroll_bar_x1 = Config.width - 2
        self.scroll_bar_height = Config.height / (self.max_scroll + Config.height) * Config.height

    def paint(self):
        return []


class BlockLayout:
    def __init__(self, node, parent, previous, view_source=False):
        self.view_source = view_source
        self.display_list = []
        self.cursor_x = Config.HSTEP
        self.cursor_y = Config.VSTEP
        self.weight = "normal"
        self.style = "roman"
        self.size = 12
        self.line = []
        self.sup = False

        # self.recurse(node)

        self.node = node
        self.parent = parent
        self.previous = previous
        self.children = []

        self.x = None
        self.y = None
        self.width = None
        self.height = None

        # self.max_scroll = 0 if self.cursor_y - Config.height + Config.VSTEP*1.25 < 0 else self.cursor_y - Config.height + Config.VSTEP*1.25
        # self.scroll_bar_x0 = Config.width - Config.HSTEP + 2
        # self.scroll_bar_x1 = Config.width - 2
        # self.scroll_bar_height = Config.height / (self.max_scroll + Config.height) * Config.height

        self.flush()

    def layout_mode(self):
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
                next = BlockLayout(child, self, previous)
                self.children.append(next)
                previous = next
        else:
            self.cursor_x = 0
            self.cursor_y = 0
            self.weight = "normal"
            self.style = "roman"
            self.size = 12

            self.line = []
            self.recurse(self.node)
            self.flush()
        for child in self.children:
            child.layout()

        if mode == "block":
            self.height = sum([
                child.height for child in self.children])
        else:
            self.height = self.cursor_y

    def word(self, node, word):
        # if word == "div":
        #     print(node.style["font-size"])
        color = node.style["color"]
        weight = node.style["font-weight"]
        style = node.style["font-style"]
        if style == "normal":
            style = "roman"
        size = int(float(node.style["font-size"][:-2]) * .75)
        # if size < 16:
        # print(word, size, node.style["font-size"])
        font_ = get_font(size if not self.sup else int(size/2), weight, style)
        w = font_.measure(word)

        if self.cursor_x + w > self.width:
            self.flush()

        self.line.append((self.cursor_x, word, font_, color, self.sup))
        self.cursor_x += w + font_.measure(" ")

    def open_tag(self, tag):
        if tag == "i":
            self.style = "italic"
        elif tag == "b":
            self.weight = "bold"
        elif tag == "small":
            self.size -= 2
        elif tag == "big":
            self.size += 4
        elif tag == "sup":
            self.sup = True
        elif tag == "br":
            self.flush()

    def close_tag(self, tag):
        if tag == "i":
            self.style = "roman"
        elif tag == "b":
            self.weight = "normal"
        elif tag == "small":
            self.size += 2
        elif tag == "big":
            self.size -= 4
        elif tag == "sup":
            self.sup = False
        elif tag == "p":
            self.flush()
            self.cursor_y += Config.VSTEP
        elif tag == "h1":
            self.flush(center=True)
            self.cursor_y += Config.VSTEP

    def recurse(self, node):
        # if isinstance(node, Text):
        #     prev_weight = self.weight
        #     if self.view_source:
        #         self.weight = "bold"
        #     for word in node.text.split():
        #         self.word(node, word)
        #     self.weight = prev_weight
        # elif self.view_source:
        #     self.word(f"<{node.tag}>")
        #     for child in node.children:
        #         self.recurse(child)
        # else:
        #     self.open_tag(node.tag)
        #     for child in node.children:
        #         self.recurse(child)
        #     self.close_tag(node.tag)

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

    def paint(self):
        cmds = []
        # if isinstance(self.node, Element) and self.node.tag == "pre":
        #     x2, y2 = self.x + self.width, self.y + self.height
        #     rect = DrawRect(self.x, self.y, x2, y2, "gray")
        #     cmds.append(rect)
        if self.layout_mode() == "inline":
            for x, y, word, font_, color in self.display_list:
                cmds.append(DrawText(x, y, word, font_, color))
        bgcolor = self.node.style.get("background-color",
                                      "transparent")
        if bgcolor != "transparent":
            x2, y2 = self.x + self.width, self.y + self.height
            rect = DrawRect(self.x, self.y, x2, y2, bgcolor)
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
    def __init__(self, x1, y1, x2, y2, color):
        self.top = y1
        self.left = x1
        self.bottom = y2
        self.right = x2
        self.color = color

    def execute(self, scroll, canvas):
        canvas.create_rectangle(
            self.left, self.top - scroll,
            self.right, self.bottom - scroll,
            width=0,
            fill=self.color)
