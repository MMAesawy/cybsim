class TabSelectorView{

    constructor(svg_width, svg_height, elementCount, elementNames){
        let vizSection = document.getElementById("elements");

        this.elementCount = elementCount;
        this.childNodes = [];

        /*
        Normally, when visualization elements are added client-side in Mesa, the constructor for the elements
        adds the DOM for the element to a div in the HTML (#elements). This is the default behavior in all
        visualization elements supplied by Mesa. Obviously this clashes with the purpose of this class, as
        you'd want these elements to be contained within this class.

        TabSelectorView gets around this by cloning these DOM elements, removing them from the
        page, then re-adding them to the DOM tree as a child of the TabSelectorView's node.
         */
        for (let i = 0; i < elementCount; i++){
            let node = vizSection.lastElementChild; // select last child of #elements
            this.childNodes.push(node);
            node.remove();
        }
        this.childNodes.reverse(); // reverse to match element ordering in server

        this.tag = document.createElement("div");

        this.tabBar = document.createElement("div");
        this.tabBar.className = "tabBar";

        for (let i = 0; i < elementCount; i++) {
            let button = document.createElement("button");
            button.tabIndex = i;
            button.innerText = elementNames[i];
            button.className = "button";
            // add event listener. binding is required to be able to reference this specific JS object
            button.addEventListener('click', this.switchTabs.bind(this));
            this.tabBar.appendChild(button);
        }
        this.tag.appendChild(this.tabBar);

        // reconstruct elements
        for (let i = 0; i < elementCount; i++){
            let div = document.createElement("div");
            div.appendChild(this.childNodes[i]);
            div.className = "tabContent";
            this.tag.appendChild(div);
        }
        vizSection.appendChild(this.tag);

        // need to remove child JS objects from elements array as the server does not realize they exist
        this.children = [];
        for (let i = 0; i < elementCount; i++){
            this.children.unshift(elements.pop()); // this modifies the elements array in the global namespace.
        }

        // finally, update page css
        // WARNING: might not work if two tab containers are made
        let style = document.createElement('style');
        style.type = 'text/css';
        style.innerHTML = `
            /* Style the tab */
            .tabBar {
              overflow: hidden;
              border: 1px solid #ccc;
              background-color: #f1f1f1;
            }
            
            /* Style the buttons that are used to open the tab content */
            .tabBar button {
              background-color: inherit;
              float: left;
              border: none;
              outline: none;
              cursor: pointer;
              padding: 14px 16px;
              transition: 0.3s;
            }
            
            /* Change background color of buttons on hover */
            .tabBar button:hover {
              background-color: #ddd;
            }
            
            /* Create an active/current tablink class */
            .tabBar button.active {
              background-color: #ccc;
            }
            
            /* Style the tab content */
            .tabContent {
              display: none;
              padding: 6px 12px;
              border: 1px solid #ccc;
              border-top: none;
            } 
        `;
        document.getElementsByTagName('head')[0].appendChild(style);

        // click first tab as to load it by default
        this.tabBar.childNodes[0].click();
    }

    switchTabs(evt){
        for (let i = 0; i < this.elementCount; i++) {
            // hide all tabs
            this.childNodes[i].parentNode.style.display = "none";
            // remove the class "active" from all tab buttons
            this.tabBar.childNodes[i].className = this.tabBar.childNodes[i].className.replace(" active", "");
        }

        // Show the current tab, and add an "active" class to the button that opened the tab
        let tabIndex = Number(evt.currentTarget.getAttribute("tabIndex"));
        this.childNodes[tabIndex].parentNode.style.display = "block";
        evt.currentTarget.className += " active";
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
