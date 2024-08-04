import tkinter


class Browser:
    WIDTH, HEIGHT = 800, 600

    def __init__(self):
        self.window = tkinter.Tk()
        self.canvas = tkinter.Canvas(
            self.window,
            width=self.WIDTH,
            height=self.HEIGHT
        )
        self.canvas.pack()

    def load(self, url):
        # ...
        self.canvas.create_rectangle(10, 20, 400, 300)
        self.canvas.create_oval(100, 100, 150, 150)
        self.canvas.create_text(200, 150, text="Hi!")