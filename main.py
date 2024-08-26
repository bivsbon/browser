import tkinter

from utils.url import URL
from browser import Browser


ENTITIES = {
    "&lt;": "<",
    "&gt;": ">"
}


def print_tree(node, indent=0):
    print(" " * indent, node)
    for child in node.children:
        print_tree(child, indent + 2)


if __name__ == "__main__":
    # uri = "data:text/html,<title>Formatting Text | Web Browser Engineering</title>\n\n</head>\n\n<body>\n\n\n<header>\n<h1 class=\"title\">Formatting Text</h1>\n<a href=\"https://twitter.com/browserbook\">Twitter</a> ·\n<a href=\"https://browserbook.substack.com/\">Blog</a> ·\n<a href=\"https://patreon.com/browserengineering\">Patreon</a> ·\n<a href=\"https://github.com/browserengineering/book/discussions\">Discussions</a>\n</header>\n\n<nav class=\"links\">\n  Chapter 3 of <a href=\"index.html\" title=\"Table of Contents\">Web Browser Engineering abc</a>"
    # uri = ("data:text/html,<p>abcoqwidjqwoid qwd qwdowijqwjo oj owqdjio iojwqioj ojiwqdiojw doijwqdoij<p>abcoqwidjqwoid qwd qwdowijqwjo oj owqdjio iojwqioj ojiwqdiojw doijwqdoij</p>")
    # uri = "https://browser.engineering/examples/example3-sizes.html"
    uri = "https://browser.engineering/styles.html"
    # uri = "file://browser.engineering/text.html"
    # uri = "file://index.html"
    # uri = "view-source:https://browser.engineering/text.html"

    Browser().new_tab(URL(uri))
    tkinter.mainloop()
    # body = URL(uri, 0).request()
    # tree = HTMLParser(body).parse()
    # print_tree(tree, 0)
    # load(URL(sys.argv[1], 0))
