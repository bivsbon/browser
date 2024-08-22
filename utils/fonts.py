import tkinter
from tkinter import font

FONTS = {}


def get_font(size, weight, style):
    key = (size, weight, style)
    if key not in FONTS:
        font_ = tkinter.font.Font(size=size, weight=weight, slant=style)
        label = tkinter.Label(font=font_)
        FONTS[key] = (font_, label)
    return FONTS[key][0]
