import tkinter

from layout import DocumentLayout
from html.element import Element
from css.css_parser import CSSParser
from html.parser import HTMLParser
from utils.url import URL
from utils.config import Config

DEFAULT_STYLE_SHEET = CSSParser(open("style.css").read()).parse()


class Browser:
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
            width=Config.width,
            height=Config.height
        )
        self.canvas.pack(fill=tkinter.BOTH, expand=True)
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Up>", self.scrollup)
        self.window.bind("<MouseWheel>", self.scroll_mouse_wheel)
        self.window.bind("<Configure>", self.resize)

    def resize(self, e: tkinter.Event):
        if Config.width != e.width or Config.height != e.height:
            Config.width = e.width
            Config.height = e.height
            self.document = DocumentLayout(self.nodes)
            self.document.layout()
            self.display_list = []
            paint_tree(self.document, self.display_list)
            self.draw()

    def scrolldown(self, e, scroll_step=Config.SCROLL_STEP):
        self.scroll += scroll_step
        if self.scroll > self.document.max_scroll:
            self.scroll = self.document.max_scroll
        self.draw()

    def scrollup(self, e, scroll_step=Config.SCROLL_STEP):
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
        self.view_source_enable = (url.scheme == "view-source")
        self.nodes = HTMLParser(body).parse()
        rules = DEFAULT_STYLE_SHEET.copy()
        style(self.nodes, rules)
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
            if cmd.top > self.scroll + Config.height:
                continue
            if cmd.bottom < self.scroll:
                continue
            cmd.execute(self.scroll, self.canvas)

        self.draw_scrollbar()

    def draw_scrollbar(self):
        if self.document.max_scroll != 0:
            y0 = self.scroll / self.document.max_scroll * (Config.height - self.document.scroll_bar_height)
            self.canvas.create_rectangle(self.document.scroll_bar_x0,
                                         y0,
                                         self.document.scroll_bar_x1,
                                         y0 + self.document.scroll_bar_height,
                                         fill="red")


def paint_tree(layout_object, display_list: list):
    display_list.extend(layout_object.paint())

    for child in layout_object.children:
        paint_tree(child, display_list)


def style(node, rules: list):
    node.style = {}
    for selector, body in rules:
        if not selector.matches(node):
            continue
        for property_, value in body.items():
            node.style[property_] = value
    if isinstance(node, Element) and "style" in node.attributes:
        pairs = CSSParser(node.attributes["style"]).body()
        for property_, value in pairs.items():
            node.style[property_] = value
    for child in node.children:
        style(child, rules)
