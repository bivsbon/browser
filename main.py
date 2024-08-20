import gzip
import socket
import ssl
import tkinter
from tkinter import font

ENTITIES = {
    "&lt;": "<",
    "&gt;": ">"
}
BLOCK_ELEMENTS = [
    "html", "body", "article", "section", "nav", "aside",
    "h1", "h2", "h3", "h4", "h5", "h6", "hgroup", "header",
    "footer", "address", "p", "hr", "pre", "blockquote",
    "ol", "ul", "menu", "li", "dl", "dt", "dd", "figure",
    "figcaption", "main", "div", "table", "form", "fieldset",
    "legend", "details", "summary"
]
WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18
FONTS = {}


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


class URLMalformedException(Exception):
    pass


class Text:
    def __init__(self, text, parent):
        self.text = text
        self.children = []
        self.parent = parent

    def __repr__(self):
        return repr(self.text)


class Element:
    def __init__(self, tag: str, attributes: dict, parent):
        self.tag = tag
        self.attributes = attributes
        self.children = []
        self.parent = parent

    def __repr__(self):
        return "<" + self.tag + ">"


class DrawText:
    def __init__(self, x1, y1, text, font):
        self.top = y1
        self.left = x1
        self.text = text
        self.font = font
        self.bottom = y1 + font.metrics("linespace")

    def execute(self, scroll, canvas):
        canvas.create_text(
            self.left, self.top - scroll,
            text=self.text,
            font=self.font,
            anchor='nw')


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
        self.width = WIDTH - 2 * HSTEP
        self.x = HSTEP
        self.y = VSTEP

        child = BlockLayout(self.node, self, None)
        self.children.append(child)
        child.layout()
        self.height = child.height
        self.max_scroll = 0 if self.height - HEIGHT + 2*VSTEP < 0 else self.height - HEIGHT + 2*VSTEP
        self.scroll_bar_x0 = WIDTH - HSTEP + 2
        self.scroll_bar_x1 = WIDTH - 2
        self.scroll_bar_height = HEIGHT / (self.max_scroll + HEIGHT) * HEIGHT

    def paint(self):
        return []


class BlockLayout:
    def __init__(self, node, parent, previous, view_source=False):
        self.view_source = view_source
        self.display_list = []
        self.cursor_x = HSTEP
        self.cursor_y = VSTEP
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

        # self.max_scroll = 0 if self.cursor_y - HEIGHT + VSTEP*1.25 < 0 else self.cursor_y - HEIGHT + VSTEP*1.25
        # self.scroll_bar_x0 = WIDTH - HSTEP + 2
        # self.scroll_bar_x1 = WIDTH - 2
        # self.scroll_bar_height = HEIGHT / (self.max_scroll + HEIGHT) * HEIGHT

        self.flush()

    def layout_mode(self):
        if isinstance(self.node, Text):
            return "inline"
        elif any([isinstance(child, Element) and child.tag in BLOCK_ELEMENTS for child in self.node.children]):
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

    def word(self, word):
        font_ = get_font(self.size if not self.sup else int(self.size/2), self.weight, self.style)
        w = font_.measure(word)

        if self.cursor_x + w > self.width:
            self.flush()

        self.line.append((self.cursor_x, word, font_, self.sup))
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
            self.cursor_y += VSTEP
        elif tag == "h1":
            self.flush(center=True)
            self.cursor_y += VSTEP

    def recurse(self, tree):
        if isinstance(tree, Text):
            prev_weight = self.weight
            if self.view_source:
                self.weight = "bold"
            for word in tree.text.split():
                self.word(word)
            self.weight = prev_weight
        elif self.view_source:
            self.word(f"<{tree.tag}>")
            for child in tree.children:
                self.recurse(child)
        else:
            self.open_tag(tree.tag)
            for child in tree.children:
                self.recurse(child)
            self.close_tag(tree.tag)

    def flush(self, center=False):
        if not self.line:
            return

        if center:
            center_offset = (WIDTH - HSTEP - self.cursor_x) / 2
        else:
            center_offset = 0

        # Find the tallest word
        metrics = [font_.metrics() for x, word, font_, sup in self.line]
        max_ascent = max([metric["ascent"] for metric in metrics])

        # Calculate baseline based on tallest word than place each word relative to that line
        baseline = self.cursor_y + 1.25 * max_ascent
        for rel_x, word, font_, sup in self.line:
            x = self.x + rel_x
            if sup:
                y = self.y + baseline - font_.metrics("ascent") * 2
            else:
                y = self.y + baseline - font_.metrics("ascent")
            self.display_list.append((x + center_offset, y, word, font_))

        # Move cursor_y far enough down below baseline to account for the deepest descender
        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = baseline + 1.25 * max_descent

        self.cursor_x = 0
        self.line = []

    def paint(self):
        cmds = []
        if isinstance(self.node, Element) and self.node.tag == "pre":
            x2, y2 = self.x + self.width, self.y + self.height
            rect = DrawRect(self.x, self.y, x2, y2, "gray")
            cmds.append(rect)
        if self.layout_mode() == "inline":
            for x, y, word, font_ in self.display_list:
                cmds.append(DrawText(x, y, word, font_))
        return cmds


class URL:
    _SUPPORTED_SCHEME = ["http", "https", "file", "data", "view-source", "about"]
    _MAX_REDIRECTS = 2

    def __init__(self, url: str, n_redirects: int):
        self.scheme = self._get_scheme(url)
        self.n_redirects = n_redirects
        if not self.scheme:
            self.scheme = "about"
            self.url = "blank"
            return

        try:
            if self.scheme == "http" or self.scheme == "https":
                self._parse_url_http(url)
            elif self.scheme == "file":
                self._parse_url_file(url)
            elif self.scheme == "data":
                self._parse_url_data(url)
            elif self.scheme == "view-source":
                self._parse_url_view_source(url)
            elif self.scheme == "about":
                pass
        except URLMalformedException:
            self.scheme = "about"
            self.url = "blank"

    def request(self) -> str:
        if self.scheme == "http" or self.scheme == "https":
            return self._request_http_and_https()
        elif self.scheme == "file":
            return self._request_file()
        elif self.scheme == "data":
            return self._request_data()
        elif self.scheme == "view-source":
            return self._request_view_source()
        elif self.scheme == "about":
            return self._request_about()

    def _request_http_and_https(self) -> str:
        s = socket.socket(
            family=socket.AF_INET,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )
        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)

        s.connect((self.host, self.port))
        request = "GET {} HTTP/1.0\r\n".format(self.path)
        request += "Host: {}\r\n".format(self.host)
        request += "Connection: {}\r\n".format("close")
        request += "User-Agent: {}\r\n".format("Quack Quack")
        request += "Accept-Encoding: {}\r\n".format("gzip")
        request += "\r\n"
        s.send(request.encode("utf8"))

        response = s.makefile("rb", encoding="utf8", newline="\r\n")

        statusline = response.readline().decode('utf-8')
        version, status, explanation = statusline.split(" ", 2)

        response_headers = {}
        while True:
            line = response.readline().decode('utf-8')
            if line == "\r\n":
                break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()

        if status.startswith("3"):
            if self.n_redirects < self._MAX_REDIRECTS:
                redirect_url = response_headers["location"]
                content = URL(self._parse_redirect_url(redirect_url), self.n_redirects + 1).request()
                s.close()
                return content
        if "content-encoding" not in response_headers:
            content = response.read().decode("utf8")
        elif response_headers["content-encoding"] == "gzip":
            content = gzip.decompress(response.read()).decode("utf-8")
        s.close()

        return content

    def _request_file(self) -> str:
        with open(self.url, "r") as f:
            return f.read()

    def _request_data(self) -> str:
        return self.data

    def _request_view_source(self) -> str:
        return self.sub_url._request_http_and_https()

    def _request_about(self) -> str:
        return ""

    def _get_scheme(self, url: str):
        for scheme in self._SUPPORTED_SCHEME:
            if url.startswith(scheme):
                return scheme
        return None

    def _parse_url_http(self, url: str):
        url = url.split("://", 1)[1]
        if self.scheme == "http":
            self.port = 80
        elif self.scheme == "https":
            self.port = 443

        if "/" not in url:
            url = url + "/"
        self.host, url = url.split("/", 1)
        self.path = "/" + url
        self.url = url

        if ":" in self.host:
            self.host, port = self.host.split(":", 1)
            self.port = int(port)

    def _parse_url_file(self, url: str):
        self.url = url.split("://", 1)[1]

    def _parse_url_data(self, url: str):
        data = url.split(":", 1)[1]
        media, data = data.split(",", 1)
        assert media in ["text/html"]
        self.data = data

    def _parse_url_view_source(self, url: str):
        url = url.split(":", 1)[1]
        self.sub_url = URL(url, self.n_redirects)

    def _parse_redirect_url(self, value):
        if value.startswith("/"):
            return f"{self.scheme}://{self.host}:{self.port}{value}"
        else:
            return value


class Browser:
    SCROLL_STEP = 100

    layout = None
    display_list = []
    nodes = None
    view_source_enable = False
    document = None

    scroll = 0

    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=WIDTH,
            height=HEIGHT
        )
        self.canvas.pack(fill=tkinter.BOTH, expand=True)
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Up>", self.scrollup)
        self.window.bind("<MouseWheel>", self.scroll_mouse_wheel)
        self.window.bind("<Configure>", self.resize)

    def resize(self, e: tkinter.Event):
        global WIDTH, HEIGHT

        if WIDTH != e.width or HEIGHT != e.height:
            WIDTH = e.width
            HEIGHT = e.height
            self.document = DocumentLayout(self.nodes)
            self.document.layout()
            self.display_list = []
            paint_tree(self.document, self.display_list)
            # self.display_list = self.layout.display_list
            self.draw()

    def scrolldown(self, e, scroll_step=SCROLL_STEP):
        self.scroll += scroll_step
        if self.scroll > self.document.max_scroll:
            self.scroll = self.document.max_scroll
        self.draw()

    def scrollup(self, e, scroll_step=SCROLL_STEP):
        self.scroll -= scroll_step
        if self.scroll < 0:
            self.scroll = 0
        self.draw()

    def scroll_mouse_wheel(self, e: tkinter.Event):
        if e.delta > 0:
            self.scrollup(e, 7 * e.delta)
        else:
            self.scrolldown(e, -7 * e.delta)

    def load(self, url: URL):
        body = url.request()
        self.view_source_enable = url.scheme == "view-source"
        self.nodes = HTMLParser(body).parse()
        self.document = DocumentLayout(self.nodes)
        self.document.layout()
        self.display_list = []
        paint_tree(self.document, self.display_list)

        # self.layout = BlockLayout(self.nodes, view_source=self.view_source_enable)
        # self.display_list = self.layout.display_list
        self.draw()

    def draw(self):
        self.canvas.delete("all")

        for cmd in self.display_list:
            if cmd.top > self.scroll + HEIGHT:
                continue
            if cmd.bottom < self.scroll:
                continue
            cmd.execute(self.scroll, self.canvas)

        # for x, y, c, font_ in self.display_list:
        #     if y > self.scroll + HEIGHT:
        #         continue
        #     if y + VSTEP < self.scroll:
        #         continue
        #
        #     self.canvas.create_text(x, y - self.scroll, text=c, font=font_, anchor="nw")

        # Draw scrollbar
        if self.document.max_scroll != 0:
            y0 = self.scroll / self.document.max_scroll * (HEIGHT - self.document.scroll_bar_height)
            self.canvas.create_rectangle(self.document.scroll_bar_x0,
                                         y0,
                                         self.document.scroll_bar_x1,
                                         y0 + self.document.scroll_bar_height,
                                         fill="red")


def lex(body: str) -> list:
    out = []
    buffer = ""
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
            if buffer: out.append(Text(buffer))
            buffer = ""
        elif c == ">":
            in_tag = False
            out.append(Element(buffer))
            buffer = ""
        else:
            buffer += c
    if not in_tag and buffer:
        out.append(Text(buffer))
    return out

    # for entity, value in ENTITIES.items():
        # result = result.replace(entity, value)
    # print(result)
    # return result


def show_source(body: str):
    for entity, value in ENTITIES.items():
        body = body.replace(entity, value)
    print(body)


def load(url: URL):
    body = url.request()
    if url.scheme == "view-source":
        show_source(body)
    else:
        print(lex(body))


def get_font(size, weight, style):
    key = (size, weight, style)
    if key not in FONTS:
        font_ = tkinter.font.Font(size=size, weight=weight, slant=style)
        label = tkinter.Label(font=font_)
        FONTS[key] = (font_, label)
    return FONTS[key][0]


def print_tree(node, indent=0):
    print(" " * indent, node)
    for child in node.children:
        print_tree(child, indent + 2)


def paint_tree(layout_object, display_list: list):
    display_list.extend(layout_object.paint())

    for child in layout_object.children:
        paint_tree(child, display_list)


if __name__ == "__main__":
    import sys

    # uri = "data:text/html,<title>Formatting Text | Web Browser Engineering</title>\n\n</head>\n\n<body>\n\n\n<header>\n<h1 class=\"title\">Formatting Text</h1>\n<a href=\"https://twitter.com/browserbook\">Twitter</a> ·\n<a href=\"https://browserbook.substack.com/\">Blog</a> ·\n<a href=\"https://patreon.com/browserengineering\">Patreon</a> ·\n<a href=\"https://github.com/browserengineering/book/discussions\">Discussions</a>\n</header>\n\n<nav class=\"links\">\n  Chapter 3 of <a href=\"index.html\" title=\"Table of Contents\">Web Browser Engineering abc</a>"
    # uri = ("data:text/html,<p>abcoqwidjqwoid qwd qwdowijqwjo oj owqdjio iojwqioj ojiwqdiojw doijwqdoij<p>abcoqwidjqwoid qwd qwdowijqwjo oj owqdjio iojwqioj ojiwqdiojw doijwqdoij</p>")
    # uri = "https://browser.engineering/examples/example3-sizes.html"
    uri = "https://browser.engineering/text.html"
    # uri = "file://browser.engineering/text.html"
    # uri = "file://index.html"
    # uri = "view-source:https://browser.engineering/text.html"

    Browser().load(URL(uri, 0))
    tkinter.mainloop()
    # body = URL(uri, 0).request()
    # tree = HTMLParser(body).parse()
    # print_tree(tree, 0)
    # load(URL(sys.argv[1], 0))
