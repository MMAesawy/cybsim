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

class HorizontalCompositeContainer(VisualizationElement):
    local_includes = ["./visualization/HorizontalCompositeContainer.js"]

    def __init__(self, elements, weights=None, canvas_height=200, canvas_width=500, gap_size=5):
        super().__init__()

        if weights and len(elements) != len(weights):
            raise AttributeError("elements and weights lists do not have equal sizes.")
        if not elements:
            raise AttributeError("elements is empty.")
        if not isinstance(elements, list):
            raise AttributeError("elements is not a list.")

        self.canvas_height = canvas_height
        self.canvas_width = canvas_width

        self.elements = elements

        # IMPORTANT: weights will NOT scale vertically properly, unless the items also have proportional heights!!!
        # e.g items with weights of [2, 1] should have heights with the same proportions (like [400, 200])
        if not weights:
            self.weights = [1 for _ in elements]
        else:
            self.weights = weights

        """
        Normally, when visualization elements are added client-side in Mesa, the constructor for the elements
        adds the DOM for the element to a div in the HTML (#elements). This is the default behavior in all 
        visualization elements supplied by Mesa. Obviously this clashes with the purpose of this class, as
        you'd want these elements to be contained within this class.
        
        HorizontalCompositeContainer gets around this by cloning these DOM elements, removing them from the
        page, then re-adding them to the DOM tree as a child of the HorizontalCompositeContainer's node.
        As such, the code for the container must be called AFTER the code for the contained items are called.
        """

        self.js_code = ""
        for e in self.elements:
            # Aggregate includes
            self.local_includes += e.local_includes
            self.package_includes += e.package_includes
            self.js_code += e.js_code + "\n"  # is newline char necessary?

        new_element = ("new HorizontalCompositeContainer({}, {}, {}, {}, {})".
                       format(self.canvas_width, self.canvas_height, len(self.elements), self.weights, gap_size))
        self.js_code += "elements.push(" + new_element + ");"

    def render(self, model):
        pass  # inserted to avoid treating comment below as docstring
        """
        Since the server only directly sees this visual element, not the ones contained within, the code
        for the container must handle calling the render functions for the contained elements, both server-side
        and client-side.
        """
        #return {"data": [e.render(model) for e in self.elements]}
        return [e.render(model) for e in self.elements]


class TabSelectorView(VisualizationElement):
    local_includes = ["./visualization/TabSelectorView.js"]

    def __init__(self, elements, element_names=None, canvas_height=200, canvas_width=500):
        super().__init__()

        if element_names and len(elements) != len(element_names):
            raise AttributeError("elements and weights lists do not have equal sizes.")
        if not elements:
            raise AttributeError("elements is empty.")
        if not isinstance(elements, list):
            raise AttributeError("elements is not a list.")

        self.canvas_height = canvas_height
        self.canvas_width = canvas_width

        self.elements = elements

        # IMPORTANT: weights will NOT scale vertically properly, unless the items also have proportional heights!!!
        # e.g items with weights of [2, 1] should have heights with the same proportions (like [400, 200])
        if not element_names:
            self.element_names = ["View %d" % i for i in range(1, len(elements) + 1)]
        else:
            self.element_names = element_names

        """
        Normally, when visualization elements are added client-side in Mesa, the constructor for the elements
        adds the DOM for the element to a div in the HTML (#elements). This is the default behavior in all 
        visualization elements supplied by Mesa. Obviously this clashes with the purpose of this class, as
        you'd want these elements to be contained within this class.

        HorizontalCompositeContainer gets around this by cloning these DOM elements, removing them from the
        page, then re-adding them to the DOM tree as a child of the HorizontalCompositeContainer's node.
        As such, the code for the container must be called AFTER the code for the contained items are called.
        """

        self.js_code = ""
        for e in self.elements:
            # Aggregate includes
            self.local_includes += e.local_includes
            self.package_includes += e.package_includes
            self.js_code += e.js_code + "\n"  # is newline char necessary?

        new_element = ("new TabSelectorView({}, {}, {}, {})".
                       format(self.canvas_width, self.canvas_height, len(self.elements), self.element_names))
        self.js_code += "elements.push(" + new_element + ");"

    def render(self, model):
        pass  # inserted to avoid treating comment below as docstring
        """
        Since the server only directly sees this visual element, not the ones contained within, the code
        for the container must handle calling the render functions for the contained elements, both server-side
        and client-side.
        """
        # return {"data": [e.render(model) for e in self.elements]}
        return [e.render(model) for e in self.elements]

