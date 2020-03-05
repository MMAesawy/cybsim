from mesa.visualization.ModularVisualization import VisualizationElement


class NetworkModule(VisualizationElement):
    local_includes = ["./visualization/d3.v5.min.js",
                      "./visualization/CustomNetworkModule.js",
                      "./visualization/fisheye.js"]

    def __init__(self, portrayal_method, canvas_height=500, canvas_width=500):
        super().__init__()

        self.portrayal_method = portrayal_method
        self.canvas_height = canvas_height
        self.canvas_width = canvas_width
        new_element = ("new NetworkModule({}, {})".
                       format(self.canvas_width, self.canvas_height))
        self.js_code = "elements.push(" + new_element + ");"

    def render(self, model):
        return self.portrayal_method(model.G)