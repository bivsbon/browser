INITIAL_WIDTH, INITIAL_HEIGHT = 800, 600


class Config:
    width = INITIAL_WIDTH
    height = INITIAL_HEIGHT

    SCROLL_STEP = 100

    HSTEP, VSTEP = 13, 18

    BLOCK_ELEMENTS = [
        "html", "body", "article", "section", "nav", "aside",
        "h1", "h2", "h3", "h4", "h5", "h6", "hgroup", "header",
        "footer", "address", "p", "hr", "pre", "blockquote",
        "ol", "ul", "menu", "li", "dl", "dt", "dd", "figure",
        "figcaption", "main", "div", "table", "form", "fieldset",
        "legend", "details", "summary"
    ]
    INHERITED_PROPERTIES = {
        "font-size": "16px",
        "font-style": "normal",
        "font-weight": "normal",
        "color": "black",
    }
    INPUT_WIDTH_PX = 200

    @classmethod
    def set_width(cls, width):
        Config.width = width

    @classmethod
    def set_height(cls, height):
        Config.height = height
