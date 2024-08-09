import gzip
import socket
import ssl
import tkinter
from tkinter import font

ENTITIES = {
    "&lt;": "<",
    "&gt;": ">"
}
WIDTH, HEIGHT = 800, 600
HSTEP, VSTEP = 13, 18


class URLMalformedException(Exception):
    pass


class Text:
    def __init__(self, text):
        self.text = text


class Tag:
    def __init__(self, tag):
        self.tag = tag


class Layout:
    def __init__(self, tokens):
        self.display_list = []
        self.cursor_x = HSTEP
        self.cursor_y = VSTEP
        self.weight = "normal"
        self.style = "roman"
        self.size = 12
        self.line = []

        for tok in tokens:
            self.token(tok)

        self.max_scroll = 0 if self.cursor_y - HEIGHT < 0 else self.cursor_y - HEIGHT
        self.scroll_bar_x0 = WIDTH - HSTEP + 2
        self.scroll_bar_x1 = WIDTH - 2
        self.scroll_bar_height = HEIGHT / (self.max_scroll + HEIGHT) * HEIGHT

        self.flush()

    def word(self, word):
        font_ = tkinter.font.Font(
            size=self.size,
            weight=self.weight,
            slant=self.style,
        )
        w = font_.measure(word)

        # Break to new line
        if self.cursor_x + w > WIDTH - HSTEP:
            self.cursor_y += font_.metrics("linespace") * 1.25
            self.cursor_x = HSTEP

        self.line.append((self.cursor_x, word, font_))
        # self.display_list.append((self.cursor_x, self.cursor_y, word, font_))
        self.cursor_x += w + font_.measure(" ")

        if self.cursor_x + w > WIDTH - HSTEP:
            self.flush()

        # if self.cursor_x >= WIDTH - HSTEP:
        #     self.cursor_y += VSTEP
        #     self.cursor_x = HSTEP

    def token(self, tok):
        if isinstance(tok, Text):
            for word in tok.text.split():
                self.word(word)
        elif tok.tag == "i":
            self.style = "italic"
        elif tok.tag == "/i":
            self.style = "roman"
        elif tok.tag == "b":
            self.weight = "bold"
        elif tok.tag == "/b":
            self.weight = "normal"
        elif tok.tag == "small":
            self.size -= 2
        elif tok.tag == "/small":
            self.size += 2
        elif tok.tag == "big":
            self.size += 4
        elif tok.tag == "/big":
            self.size -= 4

    def flush(self):
        if not self.line:
            return

        # Find the tallest word
        metrics = [font_.metrics() for x, word, font_ in self.line]
        max_ascent = max([metric["ascent"] for metric in metrics])

        # Calculate baseline based on tallest word than place each word relative to that line
        baseline = self.cursor_y + 1.25 * max_ascent
        for x, word, font_ in self.line:
            y = baseline - font_.metrics("ascent")
            self.display_list.append((x, y, word, font_))

        # Move cursor_y far enough down below baseline to account for the deepest descender
        max_descent = max([metric["descent"] for metric in metrics])
        self.cursor_y = baseline + 1.25 * max_descent

        self.cursor_x = HSTEP
        self.line = []


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
    tokens = []
    display_list = []

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

        if e.width != 1 and e.height != 1:
            if WIDTH != e.width or HEIGHT != e.height:
                WIDTH = e.width
                HEIGHT = e.height
                self.layout = Layout(self.tokens)
                self.display_list = self.layout.display_list
                self.draw()

    def scrolldown(self, e, scroll_step=SCROLL_STEP):
        self.scroll += scroll_step
        if self.scroll > self.layout.max_scroll:
            self.scroll = self.layout.max_scroll
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
        self.tokens = lex(body)
        self.layout = Layout(self.tokens)
        self.display_list = self.layout.display_list
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        for x, y, c, font_ in self.display_list:
            if y > self.scroll + HEIGHT:
                continue
            if y + VSTEP < self.scroll:
                continue

            self.canvas.create_text(x, y - self.scroll, text=c, font=font_, anchor="nw")
            if self.layout.max_scroll != 0:
                y0 = self.scroll / self.layout.max_scroll * (HEIGHT - self.layout.scroll_bar_height)
                self.canvas.create_rectangle(self.layout.scroll_bar_x0,
                                             y0,
                                             self.layout.scroll_bar_x1,
                                             y0 + self.layout.scroll_bar_height,
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
            out.append(Tag(buffer))
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


if __name__ == "__main__":
    import sys

    uri = "data:text/html,<b><i>Hello</i></b> <small>small text</small>"
    uri = "https://browser.engineering/examples/example3-sizes.html"

    Browser().load(URL(uri, 0))
    tkinter.mainloop()
    # load(URL(sys.argv[1], 0))
