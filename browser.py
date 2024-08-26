import tkinter

from layout import DocumentLayout, DrawText, DrawOutline, DrawRect, DrawLine
from html.element import Element, Text
from css.parser import CSSParser, TagSelector
from html.parser import HTMLParser
from utils.fonts import get_font
from utils.shape import Rect
from utils.url import URL
from utils.config import Config

DEFAULT_STYLE_SHEET = CSSParser(open("style.css").read()).parse()


class Chrome:
    def __init__(self, browser):
        self.browser = browser
        self.font = get_font(20, "normal", "roman")
        self.font_height = self.font.metrics("linespace")
        self.padding = 5
        self.tabbar_top = 0
        self.tabbar_bottom = self.font_height + 2*self.padding
        self.bottom = self.tabbar_bottom
        plus_width = self.font.measure("+") + 2 * self.padding
        self.newtab_rect = Rect(
            self.padding, self.padding,
            self.padding + plus_width,
            self.padding + self.font_height)
        self.urlbar_top = self.tabbar_bottom
        self.urlbar_bottom = self.urlbar_top + self.font_height + 2 * self.padding
        self.bottom = self.urlbar_bottom

        back_width = self.font.measure("<") + 2 * self.padding
        self.back_rect = Rect(
            self.padding,
            self.urlbar_top + self.padding,
            self.padding + back_width,
            self.urlbar_bottom - self.padding)

        self.address_rect = Rect(
            self.back_rect.top + self.padding,
            self.urlbar_top + self.padding,
            Config.width - self.padding,
            self.urlbar_bottom - self.padding)

        self.focus = None
        self.address_bar = ""

    def tab_rect(self, i):
        tabs_start = self.newtab_rect.right + self.padding
        tab_width = self.font.measure("Tab X") + 2*self.padding
        return Rect(
            tabs_start + tab_width * i, self.tabbar_top,
            tabs_start + tab_width * (i + 1), self.tabbar_bottom)

    def click(self, x, y):
        self.focus = None
        if self.newtab_rect.contains_point(x, y):
            self.browser.new_tab(URL("https://browser.engineering/"))
        elif self.back_rect.contains_point(x, y):
            self.browser.active_tab.go_back()
        elif self.address_rect.contains_point(x, y):
            self.focus = "address bar"
            self.address_bar = ""
        else:
            for i, tab in enumerate(self.browser.tabs):
                if self.tab_rect(i).contains_point(x, y):
                    self.browser.active_tab = tab
                    break


    def paint(self):
        cmds = []
        cmds.append(DrawRect(
            Rect(0, 0, Config.width, self.bottom),
            "white"))
        cmds.append(DrawLine(
            0, self.bottom, Config.width,
            self.bottom, "black", 1))
        cmds.append(DrawOutline(self.newtab_rect, "black", 1))
        cmds.append(DrawText(
            self.newtab_rect.left + self.padding,
            self.newtab_rect.top,
            "+", self.font, "black"))
        for i, tab in enumerate(self.browser.tabs):
            bounds = self.tab_rect(i)
            cmds.append(DrawLine(
                bounds.left, 0, bounds.left, bounds.bottom,
                "black", 1))
            cmds.append(DrawLine(
                bounds.right, 0, bounds.right, bounds.bottom,
                "black", 1))
            cmds.append(DrawText(
                bounds.left + self.padding, bounds.top + self.padding,
                "Tab {}".format(i), self.font, "black"))

            if tab == self.browser.active_tab:
                cmds.append(DrawLine(
                    0, bounds.bottom, bounds.left, bounds.bottom,
                    "black", 1))
                cmds.append(DrawLine(
                    bounds.right, bounds.bottom, Config.width, bounds.bottom,
                    "black", 1))

        # Draw back button
        cmds.append(DrawOutline(self.back_rect, "black", 1))
        cmds.append(DrawText(
            self.back_rect.left + self.padding,
            self.back_rect.top,
            "<", self.font, "black"))

        # Draw address bar
        cmds.append(DrawOutline(self.address_rect, "black", 1))
        if self.focus == "address bar":
            cmds.append(DrawText(
                self.address_rect.left + self.padding,
                self.address_rect.top,
                self.address_bar, self.font, "black"))
            w = self.font.measure(self.address_bar)
            cmds.append(DrawLine(
                self.address_rect.left + self.padding + w,
                self.address_rect.top,
                self.address_rect.left + self.padding + w,
                self.address_rect.bottom,
                "red", 1))
        else:
            url = str(self.browser.active_tab.url)
            cmds.append(DrawText(
                self.address_rect.left + self.padding,
                self.address_rect.top,
                url, self.font, "black"))
        return cmds

    def keypress(self, char):
        if self.focus == "address bar":
            self.address_bar += char

    def enter(self):
        if self.focus == "address bar":
            self.browser.active_tab.load(URL(self.address_bar))
            self.focus = None

    def backspace(self):
        if self.focus == "address bar" and self.address_bar:
            self.address_bar = self.address_bar[:-1]


class Browser:
    def __init__(self):
        self.tabs = []
        self.active_tab = None
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=Config.width,
            height=Config.height,
            bg="white"
        )
        self.canvas.pack(fill=tkinter.BOTH, expand=True)
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Up>", self.scrollup)
        self.window.bind("<MouseWheel>", self.scroll_mouse_wheel)
        self.window.bind("<Button-1>", self.click)
        self.window.bind("<Configure>", self.resize)
        self.window.bind("<Key>", self.handle_key)
        self.window.bind("<Return>", self.handle_enter)
        self.window.bind("<BackSpace>", self.handle_backspace)

        self.chrome = Chrome(self)

    def handle_backspace(self, e: tkinter.Event):
        self.chrome.backspace()
        self.draw()

    def handle_enter(self, e: tkinter.Event):
        self.chrome.enter()
        self.draw()

    def handle_key(self, e: tkinter.Event):
        if len(e.char) == 0: return
        if not (0x20 <= ord(e.char) < 0x7f):
            return
        self.chrome.keypress(e.char)
        self.draw()

    def click(self, e: tkinter.Event):
        self.active_tab.click(e, self.chrome.bottom)
        self.chrome.click(e.x, e.y)
        self.draw()

    def scrolldown(self, e):
        self.active_tab.scrolldown(e)
        self.draw()

    def scrollup(self, e):
        self.active_tab.scrollup(e)
        self.draw()

    def resize(self, e: tkinter.Event):
        self.active_tab.resize(e)
        self.draw()

    def scroll_mouse_wheel(self, e: tkinter.Event):
        self.active_tab.scroll_mouse_wheel(e)
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        self.active_tab.draw(self.canvas, self.chrome.bottom)

        for cmd in self.chrome.paint():
            cmd.execute(0, self.canvas)

    def new_tab(self, url):
        new_tab = Tab(Config.height - self.chrome.bottom)
        new_tab.load(url)
        self.active_tab = new_tab
        self.tabs.append(new_tab)
        self.draw()


class Tab:
    def __init__(self,tab_height):
        self.layout = None
        self.display_list = []
        self.nodes = None
        self.view_source_enable = False
        self.document = None

        self.scroll = 0
        self.max_scroll = 0
        self.scroll_bar_x0 = 0
        self.scroll_bar_x1 = 0
        self.scroll_bar_height = 0

        self.url = None
        self.tab_height = tab_height

        self.history = []

    def scrolldown(self, e, scroll_step=Config.SCROLL_STEP):
        self.scroll = min(self.scroll + scroll_step, self.max_scroll)

    def scrollup(self, e, scroll_step=Config.SCROLL_STEP):
        self.scroll = max(self.scroll - scroll_step, 0)

    def scroll_mouse_wheel(self, e: tkinter.Event):
        if e.delta > 0:
            self.scrollup(e, 7 * e.delta)
        else:
            self.scrolldown(e, -7 * e.delta)

    def click(self, e: tkinter.Event, offset_y=0):
        x, y = e.x, e.y
        y += self.scroll - offset_y

        objs = [obj for obj in tree_to_list(self.document, [])
                if obj.x <= x < obj.x + obj.width
                and obj.y <= y < obj.y + obj.height]

        if not objs:
            return
        elt = objs[-1].node
        while elt:
            if isinstance(elt, Text):
                pass
            elif elt.tag == "a" and "href" in elt.attributes:
                url = self.url.resolve(elt.attributes["href"])
                print("Going to:", url.full_url)
                return self.load(url)
            elt = elt.parent

    def resize(self, e: tkinter.Event):
        if Config.width != e.width or Config.height != e.height:
            Config.width = e.width
            Config.height = e.height
            self.document = DocumentLayout(self.nodes)
            self.document.layout()
            self.calculate_scrolling()
            self.display_list = []
            paint_tree(self.document, self.display_list)

    def go_back(self):
        if self.history:
            self.history.pop()
            back = self.history.pop()
            self.load(back)

    def load(self, url: URL):
        print("Loading...")
        self.history.append(url)
        self.url = url
        body = url.request()
        self.view_source_enable = (url.scheme == "view-source")
        self.nodes = HTMLParser(body).parse()

        rules = DEFAULT_STYLE_SHEET.copy()

        # CSS
        links = [node.attributes["href"]
                 for node in tree_to_list(self.nodes, [])
                 if isinstance(node, Element)
                 and node.tag == "link"
                 and node.attributes.get("rel") == "stylesheet"
                 and "href" in node.attributes]

        for link in links:
            style_url = url.resolve(link)
            try:
                body = style_url.request()
            except:
                continue
            rules.extend(CSSParser(body).parse())

        style(self.nodes, sorted(rules, key=cascade_priority))
        style(self.nodes, rules)

        self.document = DocumentLayout(self.nodes)
        self.document.layout()

        self.calculate_scrolling()

        self.display_list = []
        paint_tree(self.document, self.display_list)

    def calculate_scrolling(self):
        self.max_scroll = max(self.document.height + 2 * Config.VSTEP - self.tab_height, 0)
        self.scroll_bar_x0 = Config.width - Config.HSTEP + 2
        self.scroll_bar_x1 = Config.width - 2
        self.scroll_bar_height = Config.height / (self.max_scroll + Config.height) * Config.height

    def draw(self, canvas, offset=0):
        for cmd in self.display_list:
            if cmd.top > self.scroll + self.tab_height:
                continue
            if cmd.bottom < self.scroll:
                continue
            cmd.execute(self.scroll - offset, canvas)

        self.draw_scrollbar(canvas, offset)

    def draw_scrollbar(self, canvas, offset=0):
        if self.max_scroll != 0:
            y0 = self.scroll / self.max_scroll * (self.tab_height - self.scroll_bar_height) + offset
            canvas.create_rectangle(self.scroll_bar_x0,
                                    y0,
                                    self.scroll_bar_x1,
                                    y0 + self.scroll_bar_height,
                                    fill="red")


def paint_tree(layout_object, display_list: list):
    display_list.extend(layout_object.paint())

    for child in layout_object.children:
        paint_tree(child, display_list)


def style(node, rules: list):
    node.style = {}
    # Set defaut properties
    for property_, default_value in Config.INHERITED_PROPERTIES.items():
        if node.parent:
            node.style[property_] = node.parent.style[property_]
        else:
            node.style[property_] = default_value

    for selector, body in rules:
        if not selector.matches(node):
            continue
        for property_, value in body.items():
            node.style[property_] = value

    # Inline CSS
    if isinstance(node, Element) and "style" in node.attributes:
        pairs = CSSParser(node.attributes["style"]).body()
        for property_, value in pairs.items():
            node.style[property_] = value

    if node.style["font-size"].endswith("%"):
        if node.parent:
            parent_font_size = node.parent.style["font-size"]
        else:
            parent_font_size = Config.INHERITED_PROPERTIES["font-size"]
        node_pct = float(node.style["font-size"][:-1]) / 100
        parent_px = float(parent_font_size[:-2])
        node.style["font-size"] = str(node_pct * parent_px) + "px"

    for child in node.children:
        style(child, rules)


def tree_to_list(tree, li):
    li.append(tree)
    for child in tree.children:
        tree_to_list(child, li)
    return li


def cascade_priority(rule):
    """
    Calculate priority of this CSS rule
    """
    selector, body = rule
    return selector.priority
