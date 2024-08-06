import gzip
import socket
import ssl
import tkinter
from tkinter import font

ENTITIES = {
    "&lt;": "<",
    "&gt;": ">"
}


class URLMalformedException(Exception):
    pass


class Text:
    def __init__(self, text):
        self.text = text


class Tag:
    def __init__(self, tag):
        self.tag = tag


class URL:
    _SUPPORTED_SCHEME = ["http", "https", "file", "data", "view-source", "about"]
    _MAX_REDIRECTS = 2

    def __init__(self, url: str, n_redirects: int):
        print("Redirect =", n_redirects)
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
    WIDTH, HEIGHT = 800, 600
    HSTEP, VSTEP = 13, 18
    SCROLL_STEP = 100

    text = ""
    scroll = 0
    max_scroll = 0
    display_list = []
    scroll_bar_x0 = 0
    scroll_bar_x1 = 0
    scroll_bar_height = 0

    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=self.WIDTH,
            height=self.HEIGHT
        )
        self.canvas.pack(fill=tkinter.BOTH, expand=True)
        self.window.bind("<Down>", self.scrolldown)
        self.window.bind("<Up>", self.scrollup)
        self.window.bind("<MouseWheel>", self.scroll_mouse_wheel)
        self.window.bind("<Configure>", self.resize)

    def resize(self, e: tkinter.Event):
        self.WIDTH = e.width
        self.HEIGHT = e.height
        self.display_list = self.layout(self.text)
        self.draw()

    def scrolldown(self, e, scroll_step=SCROLL_STEP):
        self.scroll += scroll_step
        if self.scroll > self.max_scroll:
            self.scroll = self.max_scroll
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

    def layout(self, tokens: list):
        weight = "normal"
        style = "roman"
        font_ = tkinter.font.Font()
        display_list = []
        cursor_x, cursor_y = self.HSTEP, self.VSTEP
        for tok in tokens:
            if isinstance(tok, Text):
                for word in tok.text.split():
                    font_ = tkinter.font.Font(
                        family="Times",
                        size=16,
                        weight=weight,
                        slant=style,
                    )
                    w = font_.measure(word)

                    if cursor_x + w > self.WIDTH - self.HSTEP:
                        cursor_y += font_.metrics("linespace") * 1.25
                        cursor_x = self.HSTEP

                    display_list.append((cursor_x, cursor_y, word, font_))
                    cursor_x += w + font_.measure(" ")

                    if cursor_x >= self.WIDTH - self.HSTEP:
                        cursor_y += self.VSTEP
                        cursor_x = self.HSTEP
            elif tok.tag == "i":
                style = "italic"
            elif tok.tag == "/i":
                style = "roman"
            elif tok.tag == "b":
                weight = "bold"
            elif tok.tag == "/b":
                weight = "normal"
        self.max_scroll = 0 if cursor_y - self.HEIGHT < 0 else cursor_y - self.HEIGHT
        self.scroll_bar_x0 = self.WIDTH - self.HSTEP + 2
        self.scroll_bar_x1 = self.WIDTH - 2
        self.scroll_bar_height = self.HEIGHT / (self.max_scroll + self.HEIGHT) * self.HEIGHT
        return display_list

    def load(self, url: URL):
        body = url.request()
        self.text = lex(body)
        self.display_list = self.layout(self.text)
        self.draw()

    def draw(self):
        self.canvas.delete("all")
        for x, y, c, font_ in self.display_list:
            if y > self.scroll + self.HEIGHT:
                continue
            if y + self.VSTEP < self.scroll:
                continue

            self.canvas.create_text(x, y - self.scroll, text=c, font=font_, anchor="nw")
            if self.max_scroll != 0:
                y0 = self.scroll / self.max_scroll * (self.HEIGHT - self.scroll_bar_height)
                self.canvas.create_rectangle(self.scroll_bar_x0,
                                             y0,
                                             self.scroll_bar_x1,
                                             y0 + self.scroll_bar_height,
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

    for entity, value in ENTITIES.items():
        result = result.replace(entity, value)
    # print(result)
    return result


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

    Browser().load(URL(sys.argv[1], 0))
    tkinter.mainloop()
    # load(URL(sys.argv[1], 0))
