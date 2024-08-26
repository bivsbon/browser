import gzip
import socket
import ssl


class URLMalformedException(Exception):
    pass


class URL:
    _SUPPORTED_SCHEME = ["http", "https", "file", "data", "view-source", "about"]
    _MAX_REDIRECTS = 2

    def __init__(self, url: str, n_redirects: int = 0):
        self.full_url = url
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

    def resolve(self, url):
        if "://" in url:
            return URL(url)
        if not url.startswith("/"):
            dir_, _ = self.path.rsplit("/", 1)
            while url.startswith("../"):
                _, url = url.split("/", 1)
                if "/" in dir_:
                    dir_, _ = dir_.rsplit("/", 1)
            url = dir_ + "/" + url
        if url.startswith("//"):
            return URL(self.scheme + ":" + url, 0)
        else:
            return URL(self.scheme + "://" + self.host + ":" + str(self.port) + url, 0)

    def __str__(self):
        port_part = ":" + str(self.port)
        if self.scheme == "https" and self.port == 443:
            port_part = ""
        if self.scheme == "http" and self.port == 80:
            port_part = ""
        return self.scheme + "://" + self.host + port_part + self.path
