class HorizontalCompositeContainer{

    constructor(svg_width, svg_height, elementCount, weights, gap_size=5){
        let childNodes = [];
        let vizSection = document.getElementById("elements");
        this.elementCount = elementCount;

        /*
        Normally, when visualization elements are added client-side in Mesa, the constructor for the elements
        adds the DOM for the element to a div in the HTML (#elements). This is the default behavior in all
        visualization elements supplied by Mesa. Obviously this clashes with the purpose of this class, as
        you'd want these elements to be contained within this class.

        HorizontalCompositeContainer gets around this by cloning these DOM elements, removing them from the
        page, then re-adding them to the DOM tree as a child of the HorizontalCompositeContainer's node.
         */
        weights.reverse(); // reverse to match element ordering in #elements "stack"
        for (let i = 0; i < elementCount; i++){
            let node = vizSection.lastElementChild; // select last child of #elements
            //node.removeAttribute("width"); // needed so children won't "overflow"
            childNodes.push(node);
            node.remove();
        }
        childNodes.reverse(); // reverse to match element ordering in server

        this.tag = document.createElement("div");
        this.tag.style.display = "flex";
        //this.tag.style.minHeight = "max-content";
        this.tag.style.flexDirection = "row";
        this.tag.style.alignItems = "stretch";
        this.tag.style.margin = "0 -" + gap_size + "px"; // MIGHT NOT WORK

        // reconstruct elements
        for (let i = 0; i < elementCount; i++){
            let div = document.createElement("div");
            div.style.flex = "1";
            div.style.overflow = "auto";
            div.style.flexGrow = String(weights[i]); // TODO: weight scaling does not work vertically
            div.style.padding = "0 " + gap_size + "px"; // MIGHT NOT WORK

            //div.style.display = "flex";
            //div.style.flexDirection = "column";
            //div.style.minHeight = "min-content";
            //childNodes[i].style.flex = "1";

            div.appendChild(childNodes[i]);
            this.tag.appendChild(div);
        }
        vizSection.appendChild(this.tag);

        // need to remove child JS objects from elements array as the server does not realize they exist
        this.children = [];
        for (let i = 0; i < elementCount; i++){
            this.children.unshift(elements.pop()); // this modifies the elements array in the global namespace.
        }
    }

    render(data){
        //let json_data = JSON.parse(JSON.stringify(data));
        for (let i = 0; i < this.elementCount; i++){
            this.children[i].render(data[i]);
        }
    }

    reset(){
        for (let i = 0; i < this.elementCount; i++){
            this.children[i].reset();
        }
    }
}
